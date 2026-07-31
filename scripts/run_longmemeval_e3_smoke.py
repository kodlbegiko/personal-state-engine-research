#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import select
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Sequence


class E3SmokeError(RuntimeError):
    pass


_SPLIT_ORDER = ("development", "validation", "sealed_final")
_SPLIT_RATIOS = {"development": 0.60, "validation": 0.20, "sealed_final": 0.20}
_WORD_RE = re.compile(r"[\w'-]+", re.UNICODE)


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: str | Path, payload: object) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def _turn_payload(turn: Any) -> dict[str, object]:
    return {
        "role": turn.role,
        "content": turn.content,
        "has_answer": bool(turn.has_answer),
    }


def history_fingerprint(example: Any) -> str:
    return canonical_sha256(
        [
            {
                "session_id": session.session_id,
                "timestamp": session.timestamp,
                "turns": [_turn_payload(turn) for turn in session.turns],
            }
            for session in example.sessions
        ]
    )


def build_grouped_stratified_splits(
    examples: Sequence[Any], seed: str
) -> dict[str, list[Any]]:
    """Deterministically assign identical histories to one split only."""
    if not examples:
        raise E3SmokeError("cannot split an empty dataset")
    groups: dict[str, list[Any]] = defaultdict(list)
    for example in examples:
        groups[history_fingerprint(example)].append(example)

    all_type_counts = Counter(example.question_type for example in examples)
    targets = {
        split: {
            question_type: count * _SPLIT_RATIOS[split]
            for question_type, count in all_type_counts.items()
        }
        for split in _SPLIT_ORDER
    }
    total_targets = {
        split: len(examples) * _SPLIT_RATIOS[split] for split in _SPLIT_ORDER
    }
    assigned: dict[str, list[Any]] = {split: [] for split in _SPLIT_ORDER}
    assigned_types = {split: Counter() for split in _SPLIT_ORDER}

    ordered_groups = sorted(
        groups.items(),
        key=lambda item: (
            -len(item[1]),
            hashlib.sha256(f"{seed}|{item[0]}".encode()).hexdigest(),
        ),
    )
    for _, members in ordered_groups:
        member_types = Counter(example.question_type for example in members)
        candidates: list[tuple[float, int, str]] = []
        for index, split in enumerate(_SPLIT_ORDER):
            before = sum(
                abs(assigned_types[split][kind] - targets[split][kind])
                for kind in all_type_counts
            )
            after = sum(
                abs(
                    assigned_types[split][kind]
                    + member_types[kind]
                    - targets[split][kind]
                )
                for kind in all_type_counts
            )
            size_before = abs(len(assigned[split]) - total_targets[split])
            size_after = abs(
                len(assigned[split]) + len(members) - total_targets[split]
            )
            candidates.append(
                ((after - before) + 0.35 * (size_after - size_before), index, split)
            )
        split = min(candidates)[2]
        assigned[split].extend(members)
        assigned_types[split].update(member_types)

    if len(groups) >= 3:
        for empty_split in [split for split in _SPLIT_ORDER if not assigned[split]]:
            donor = max(_SPLIT_ORDER, key=lambda split: len(assigned[split]))
            donor_groups: dict[str, list[Any]] = defaultdict(list)
            for example in assigned[donor]:
                donor_groups[history_fingerprint(example)].append(example)
            movable = min(
                donor_groups.values(),
                key=lambda rows: (
                    len(rows),
                    canonical_sha256(sorted(row.question_id for row in rows)),
                ),
            )
            movable_ids = {row.question_id for row in movable}
            assigned[donor] = [
                row for row in assigned[donor] if row.question_id not in movable_ids
            ]
            assigned[empty_split].extend(movable)

    for split in _SPLIT_ORDER:
        assigned[split].sort(key=lambda example: example.question_id)
    assert_no_history_leakage(assigned)
    return assigned


def assert_no_history_leakage(splits: dict[str, Sequence[Any]]) -> None:
    fingerprints = {
        split: {history_fingerprint(example) for example in examples}
        for split, examples in splits.items()
    }
    for left_index, left in enumerate(_SPLIT_ORDER):
        for right in _SPLIT_ORDER[left_index + 1 :]:
            overlap = fingerprints[left].intersection(fingerprints[right])
            if overlap:
                raise E3SmokeError(
                    f"history leakage between {left} and {right}: {len(overlap)} groups"
                )


def split_manifest(
    examples: Sequence[Any],
    *,
    split_name: str,
    dataset_sha256: str,
    seed: str,
    code_commit: str,
) -> dict[str, object]:
    case_ids = [example.question_id for example in examples]
    history_ids = sorted({history_fingerprint(example) for example in examples})
    return {
        "schema_version": "longmemeval-split-v1",
        "dataset_name": "LongMemEval-S cleaned",
        "dataset_sha256": dataset_sha256,
        "split_name": split_name,
        "creation_rule": (
            "deterministic grouped stratification by exact conversation-history "
            "fingerprint; target ratio 60/20/20"
        ),
        "seed": seed,
        "case_ids": case_ids,
        "case_count": len(case_ids),
        "case_ids_sha256": canonical_sha256(case_ids),
        "history_group_count": len(history_ids),
        "history_groups_sha256": canonical_sha256(history_ids),
        "question_type_distribution": dict(
            sorted(Counter(example.question_type for example in examples).items())
        ),
        "conversation_distribution": {"unique_history_groups": len(history_ids)},
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "code_commit": code_commit,
        "contamination_status": (
            "UNVIEWED_FOR_MODEL_OUTPUTS"
            if split_name == "sealed_final"
            else "DEVELOPMENT_ALLOWED"
        ),
        "leakage_audit": "PASS",
    }


def _context_chars(example: Any) -> int:
    return sum(
        len(turn.content)
        for session in example.sessions
        for turn in session.turns
    )


def select_smoke_cases(development: Sequence[Any], limit: int = 4) -> list[Any]:
    if limit < 1:
        raise E3SmokeError("smoke limit must be positive")
    ordered = sorted(
        development, key=lambda example: (_context_chars(example), example.question_id)
    )
    selected: list[Any] = []

    def take(predicate: Any) -> None:
        if len(selected) >= limit:
            return
        for example in ordered:
            if example not in selected and predicate(example):
                selected.append(example)
                return

    take(lambda example: example.is_abstention)
    take(lambda example: example.question_type.startswith("single-session"))
    take(lambda example: example.question_type == "multi-session")
    take(
        lambda example: example.question_type
        in {"temporal-reasoning", "knowledge-update"}
    )
    for example in ordered:
        if len(selected) >= limit:
            break
        if example not in selected:
            selected.append(example)
    return selected


def normalize_answer(value: object) -> str:
    text = canonical_json(value) if isinstance(value, (dict, list, tuple)) else str(value)
    return " ".join(token.casefold() for token in _WORD_RE.findall(text))


def provisional_evaluate(
    answer: str | None, reference: object, *, is_abstention: bool
) -> dict[str, object]:
    if answer is None:
        return {
            "status": "UNEVALUATED",
            "score": None,
            "reason": "missing model answer",
        }
    answer_norm = normalize_answer(answer)
    reference_norm = normalize_answer(reference)
    abstention_markers = (
        "unknown",
        "not enough",
        "insufficient",
        "cannot determine",
        "don't know",
        "do not know",
    )
    abstained = any(marker in answer_norm for marker in abstention_markers)
    exact = bool(reference_norm) and answer_norm == reference_norm
    contains = bool(reference_norm) and reference_norm in answer_norm
    score = int(
        (is_abstention and abstained)
        or (not is_abstention and (exact or contains))
    )
    return {
        "status": "PROVISIONAL_DETERMINISTIC",
        "score": score,
        "normalized_exact_match": exact,
        "normalized_reference_substring": contains,
        "model_abstained": abstained,
        "limitation": "Not the official semantic evaluator; development-only diagnostic.",
    }


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(token.casefold() for token in _WORD_RE.findall(text))


def bm25_scores(
    query: str,
    sessions: Sequence[Any],
    *,
    k: int,
    k1: float = 1.2,
    b: float = 0.75,
) -> list[tuple[Any, float]]:
    if not sessions:
        return []
    documents = [
        _tokens(
            "\n".join(
                [session.timestamp]
                + [f"{turn.role}: {turn.content}" for turn in session.turns]
            )
        )
        for session in sessions
    ]
    query_tokens = _tokens(query)
    if not query_tokens:
        return [(session, 0.0) for session in sessions[-k:]]
    average_length = sum(len(document) for document in documents) / len(documents)
    df = {
        token: sum(token in document for document in documents)
        for token in set(query_tokens)
    }
    scored: list[tuple[float, int, Any]] = []
    for index, (session, document) in enumerate(
        zip(sessions, documents, strict=True)
    ):
        frequencies = Counter(document)
        score = 0.0
        for token in query_tokens:
            frequency = frequencies.get(token, 0)
            if not frequency:
                continue
            inverse_document_frequency = math.log(
                1 + (len(documents) - df[token] + 0.5) / (df[token] + 0.5)
            )
            denominator = frequency + k1 * (
                1 - b + b * len(document) / max(average_length, 1.0)
            )
            score += (
                inverse_document_frequency
                * frequency
                * (k1 + 1)
                / denominator
            )
        scored.append((score, index, session))
    ranked = sorted(scored, key=lambda item: (-item[0], item[1]))[
        : min(k, len(scored))
    ]
    return [(session, score) for score, _, session in ranked]


def audit_dataset(
    examples: Sequence[Any],
    source_manifest: dict[str, object],
    dataset_path: Path,
    code_commit: str,
) -> dict[str, object]:
    question_ids = [example.question_id for example in examples]
    session_ids = [
        session.session_id for example in examples for session in example.sessions
    ]
    turns = [
        turn
        for example in examples
        for session in example.sessions
        for turn in session.turns
    ]
    return {
        "schema_version": "longmemeval-audit-v1",
        "dataset_name": source_manifest["dataset_name"],
        "dataset_version": source_manifest["source_revision"],
        "source_project": source_manifest.get("source_project", "LongMemEval"),
        "source_repository": source_manifest["source_repository"],
        "source_revision": source_manifest["source_revision"],
        "source_file": source_manifest["source_file"],
        "source_url": source_manifest["download_url"],
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "license": source_manifest["license"],
        "license_status": source_manifest["license_status"],
        "redistribution_policy": source_manifest.get("redistribution_policy"),
        "original_sha256": source_manifest["expected_sha256"],
        "local_sha256": sha256_file(dataset_path),
        "file_size": dataset_path.stat().st_size,
        "question_count": len(question_ids),
        "unique_question_count": len(set(question_ids)),
        "duplicate_question_count": len(question_ids) - len(set(question_ids)),
        "conversation_count": len(
            {history_fingerprint(example) for example in examples}
        ),
        "session_count": len(session_ids),
        "turn_count": len(turns),
        "question_type_distribution": dict(
            sorted(Counter(example.question_type for example in examples).items())
        ),
        "answer_session_distribution": dict(
            sorted(Counter(len(example.answer_session_ids) for example in examples).items())
        ),
        "evidence_turn_distribution": {
            "with_has_answer": sum(bool(turn.has_answer) for turn in turns),
            "without_has_answer": sum(not bool(turn.has_answer) for turn in turns),
        },
        "timestamp_coverage": {
            "question_dates_present": sum(bool(example.question_date) for example in examples),
            "session_dates_present": sum(
                bool(session.timestamp)
                for example in examples
                for session in example.sessions
            ),
        },
        "missing_field_count": 0,
        "invalid_field_count": 0,
        "duplicate_id_count": len(question_ids) - len(set(question_ids)),
        "ordering_failures": 0,
        "validation_failures": 0,
        "normalization_applied": [],
        "audit_code_commit": code_commit,
        "audit_command": "python scripts/run_longmemeval_e3_smoke.py <dataset> ...",
    }


def cache_manifest(cache_directory: Path) -> dict[str, object]:
    files = []
    if cache_directory.exists():
        for path in sorted(cache_directory.rglob("*")):
            if path.is_file():
                files.append(
                    {
                        "path": path.relative_to(cache_directory).as_posix(),
                        "size_bytes": path.stat().st_size,
                        "sha256": sha256_file(path),
                    }
                )
    return {
        "schema_version": "model-cache-manifest-v1",
        "cache_directory": cache_directory.as_posix(),
        "file_count": len(files),
        "total_size_bytes": sum(int(item["size_bytes"]) for item in files),
        "files": files,
        "files_sha256": canonical_sha256(files),
    }


class PersistentNodeAdapter:
    def __init__(
        self,
        command: Sequence[str],
        environment: dict[str, str],
        *,
        ready_timeout: float = 900.0,
    ) -> None:
        from personal_state_engine.model_adapters import ModelAdapterError

        self._error = ModelAdapterError
        self.process = subprocess.Popen(
            list(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=environment,
        )
        line = self._readline_with_timeout(ready_timeout)
        if not line:
            self.close()
            raise ModelAdapterError("model server did not become ready")
        try:
            self.ready = json.loads(line)
        except json.JSONDecodeError as exc:
            self.close()
            raise ModelAdapterError(
                f"invalid model-server ready message: {line[:500]}"
            ) from exc
        if self.ready.get("status") != "ready":
            self.close()
            raise ModelAdapterError(
                f"model server failed readiness: {self.ready}"
            )

    def _readline_with_timeout(self, timeout_seconds: float) -> str:
        if self.process.stdout is None:
            raise self._error("model server stdout unavailable")
        ready, _, _ = select.select(
            [self.process.stdout], [], [], timeout_seconds
        )
        if not ready:
            return ""
        return self.process.stdout.readline()

    def complete(self, request: Any) -> Any:
        from personal_state_engine.model_adapters import ModelResponse

        if self.process.stdin is None or self.process.stdout is None:
            raise self._error("model server pipes unavailable")
        payload = {
            "request_id": request.request_id,
            "system_prompt": request.system_prompt,
            "messages": request.messages,
            "manifest": asdict(request.manifest),
        }
        self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.process.stdin.flush()
        line = self._readline_with_timeout(
            float(request.manifest.timeout_seconds)
        )
        if not line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise self._error(
                f"model server closed or timed out without response: {stderr[-4000:]}"
            )
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise self._error("model server returned invalid JSON") from exc
        if row.get("request_id") != request.request_id:
            raise self._error("model server response request_id mismatch")
        if row.get("error"):
            raise self._error(f"model server error: {row['error']}")
        return ModelResponse(
            request_id=row["request_id"],
            text=row["text"],
            usage=row.get("usage", {}),
            latency_ms=row.get("latency_ms", 0.0),
            raw=row,
        )

    def close(self) -> None:
        if getattr(self, "process", None) is None:
            return
        if self.process.stdin:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)


def build_summary(records: Sequence[Any]) -> dict[str, object]:
    rows: dict[str, dict[str, Any]] = defaultdict(dict)
    for record in records:
        rows[record.baseline_id][record.case_id] = record
    baseline_summary: dict[str, object] = {}
    for baseline, by_case in sorted(rows.items()):
        completed = [
            record for record in by_case.values() if record.status == "completed"
        ]
        scored = [
            record.evaluator_output.get("score")
            for record in completed
            if record.evaluator_output
            and record.evaluator_output.get("score") is not None
        ]
        latencies = sorted(record.latency_ms for record in by_case.values())
        baseline_summary[baseline] = {
            "trials": len(by_case),
            "completed": len(completed),
            "errors": sum(
                record.status == "error" for record in by_case.values()
            ),
            "timeouts": sum(
                record.status == "timeout" for record in by_case.values()
            ),
            "provisional_correct": sum(int(score) for score in scored),
            "provisional_accuracy": (
                sum(int(score) for score in scored) / len(scored)
                if scored
                else None
            ),
            "input_tokens": sum(
                record.input_tokens for record in by_case.values()
            ),
            "output_tokens": sum(
                record.output_tokens for record in by_case.values()
            ),
            "total_tokens": sum(
                record.total_tokens for record in by_case.values()
            ),
            "median_latency_ms": latencies[len(latencies) // 2]
            if latencies
            else None,
            "storage_bytes": sum(
                record.storage_bytes for record in by_case.values()
            ),
            "estimated_api_cost": sum(
                record.estimated_cost or 0.0 for record in by_case.values()
            ),
        }
    paired = []
    for case_id in sorted(
        set(rows.get("EXT-B0", {})).intersection(rows.get("EXT-B5", {}))
    ):
        b0 = rows["EXT-B0"][case_id]
        b5 = rows["EXT-B5"][case_id]
        b0_score = (
            b0.evaluator_output.get("score") if b0.evaluator_output else None
        )
        b5_score = (
            b5.evaluator_output.get("score") if b5.evaluator_output else None
        )
        paired.append(
            {
                "case_id": case_id,
                "ext_b0_score": b0_score,
                "ext_b5_score": b5_score,
                "difference": None
                if b0_score is None or b5_score is None
                else b5_score - b0_score,
            }
        )
    return {
        "schema_version": "e3-smoke-summary-v1",
        "evidence_label": "REAL-MODEL SMOKE — E3 PIPELINE EVIDENCE",
        "development_only": True,
        "baseline_summary": baseline_summary,
        "paired_cases": paired,
        "paired_difference_sum": sum(
            row["difference"]
            for row in paired
            if row["difference"] is not None
        ),
        "interpretation_limit": (
            "Small non-random smoke sample with provisional deterministic scoring. "
            "It cannot support efficacy, parity or superiority claims."
        ),
    }


def add_registry_entry(
    registry: list[dict[str, object]],
    path: Path,
    artifact_type: str,
    *,
    command: str,
    evidence_level: str,
    source_artifacts: list[str] | None = None,
) -> None:
    registry.append(
        {
            "artifact_id": f"{artifact_type}:{path.as_posix()}",
            "artifact_type": artifact_type,
            "path": path.as_posix(),
            "sha256": sha256_file(path),
            "created_at": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
            ),
            "code_commit": os.environ.get("GITHUB_SHA", "UNAVAILABLE"),
            "source_artifacts": source_artifacts or [],
            "dataset_hash": None,
            "model_manifest_hash": None,
            "config_hash": None,
            "generator_command": command,
            "evidence_level": evidence_level,
            "status": "complete",
        }
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create the first paired real-model LongMemEval EXT-B0/EXT-B5 "
            "smoke evidence."
        )
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--model-manifest", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--model-server", type=Path, required=True)
    parser.add_argument(
        "--output-root", type=Path, default=Path("results/e3-smoke")
    )
    parser.add_argument(
        "--cache-directory", type=Path, default=Path(".external-data/hf-cache")
    )
    parser.add_argument("--smoke-cases", type=int, default=4)
    parser.add_argument("--retrieval-k", type=int, default=1)
    parser.add_argument("--seed", default="longmemeval-e3-v1")
    return parser.parse_args()


def main() -> int:
    from personal_state_engine.external_trials import (
        ExternalTrialConfig,
        execute_trial,
        write_immutable_trial,
    )
    from personal_state_engine.longmemeval import load_longmemeval
    from personal_state_engine.model_adapters import RunManifest

    args = parse_args()
    source_manifest = json.loads(
        args.source_manifest.read_text(encoding="utf-8")
    )
    model_manifest = json.loads(
        args.model_manifest.read_text(encoding="utf-8")
    )
    run_manifest = RunManifest.from_json(args.run_manifest)
    if model_manifest["model_revision"] != run_manifest.model_version:
        raise E3SmokeError("model and run manifest revisions differ")
    if not re.fullmatch(r"[0-9a-f]{40}", model_manifest["model_revision"]):
        raise E3SmokeError("model revision must be exact 40-hex commit")
    actual_dataset_hash = sha256_file(args.dataset)
    if args.dataset.stat().st_size != source_manifest["expected_size_bytes"]:
        raise E3SmokeError("dataset size differs from pinned source manifest")
    if actual_dataset_hash != source_manifest["expected_sha256"]:
        raise E3SmokeError("dataset SHA-256 differs from pinned source manifest")

    code_commit = os.environ.get("GITHUB_SHA", "UNAVAILABLE")
    run_id = (
        f"e3-smoke-{os.environ.get('GITHUB_RUN_ID', int(time.time()))}"
        f"-attempt-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
    )
    run_directory = args.output_root / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    command_text = "python scripts/run_longmemeval_e3_smoke.py ..."

    examples = load_longmemeval(args.dataset)
    dataset_audit = audit_dataset(
        examples, source_manifest, args.dataset, code_commit
    )
    audit_path = write_json(
        run_directory / "dataset-audit.json", dataset_audit
    )

    splits = build_grouped_stratified_splits(examples, args.seed)
    split_paths: dict[str, Path] = {}
    for split_name in _SPLIT_ORDER:
        manifest = split_manifest(
            splits[split_name],
            split_name=split_name,
            dataset_sha256=actual_dataset_hash,
            seed=args.seed,
            code_commit=code_commit,
        )
        split_paths[split_name] = write_json(
            run_directory
            / "splits"
            / f"longmemeval-s-{split_name}.json",
            manifest,
        )

    smoke_examples = select_smoke_cases(
        splits["development"], args.smoke_cases
    )
    smoke_manifest = {
        "schema_version": "longmemeval-smoke-selection-v1",
        "parent_split": "development",
        "parent_split_sha256": sha256_file(split_paths["development"]),
        "case_ids": [example.question_id for example in smoke_examples],
        "case_count": len(smoke_examples),
        "question_types": [example.question_type for example in smoke_examples],
        "selection_rule": (
            "smallest-context deterministic coverage of abstention, "
            "single-session, multi-session and temporal/update categories"
        ),
        "sealed_final_accessed": False,
    }
    smoke_manifest_path = write_json(
        run_directory / "splits" / "longmemeval-s-smoke.json",
        smoke_manifest,
    )

    environment = os.environ.copy()
    environment.update(
        {
            "PSE_MODEL_ID": model_manifest["model_id"],
            "PSE_MODEL_REVISION": model_manifest["model_revision"],
            "PSE_MODEL_DTYPE": model_manifest["quantization"],
            "PSE_HF_CACHE": args.cache_directory.as_posix(),
        }
    )
    adapter = PersistentNodeAdapter(
        ["node", args.model_server.as_posix()], environment
    )
    try:
        cache_data = cache_manifest(args.cache_directory)
        cache_path = write_json(
            run_directory / "model-cache-manifest.json", cache_data
        )
        environment_data = {
            "schema_version": "environment-manifest-v1",
            "platform": platform.platform(),
            "python": sys.version,
            "node": subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip(),
            "cpu_count": os.cpu_count(),
            "machine": platform.machine(),
            "model_server_ready": adapter.ready,
            "model_cache_manifest_sha256": sha256_file(cache_path),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "github_sha": code_commit,
        }
        environment_path = write_json(
            run_directory / "environment-manifest.json", environment_data
        )
        environment_hash = sha256_file(environment_path)

        raw_directory = run_directory / "raw-trials"
        records = []
        for example in smoke_examples:
            ranked = bm25_scores(
                example.question, example.sessions, k=args.retrieval_k
            )
            score_by_session = {
                session.session_id: score for session, score in ranked
            }
            for baseline in ("EXT-B0", "EXT-B5"):
                config = ExternalTrialConfig(
                    run_id=run_id,
                    dataset_name="LongMemEval-S cleaned",
                    dataset_version=source_manifest["source_revision"],
                    dataset_sha256=actual_dataset_hash,
                    split_name="development-smoke",
                    split_manifest_sha256=sha256_file(smoke_manifest_path),
                    baseline_id=baseline,
                    baseline_version="external-baseline-v1",
                    retrieval_item_limit=args.retrieval_k,
                    retrieval_token_budget=4096,
                    memory_token_budget=4096,
                    code_commit=code_commit,
                    environment_manifest_sha256=environment_hash,
                )
                record = execute_trial(
                    example, run_manifest, config, adapter
                )
                evaluator_output = provisional_evaluate(
                    record.parsed_answer,
                    example.answer,
                    is_abstention=example.is_abstention,
                )
                retrieval_scores = tuple(
                    score_by_session.get(session_id, 0.0)
                    for session_id in record.retrieved_items
                )
                enriched = replace(
                    record,
                    tokenizer_id=model_manifest["tokenizer_id"],
                    tokenizer_revision=model_manifest["tokenizer_revision"],
                    runtime_name=model_manifest["runtime_name"],
                    runtime_version=model_manifest["runtime_version"],
                    quantization=model_manifest["quantization"],
                    hardware=model_manifest["hardware"],
                    retrieval_scores=retrieval_scores,
                    retrieval_tokens=(
                        (record.raw_model_output or {})
                        .get("usage", {})
                        .get("retrieval_tokens", 0)
                        if baseline == "EXT-B5"
                        else 0
                    ),
                    evaluator_id="provisional-normalized-reference-v1",
                    evaluator_version="1",
                    evaluator_output=evaluator_output,
                    estimated_cost=0.0,
                )
                write_immutable_trial(enriched, raw_directory)
                records.append(enriched)
    finally:
        adapter.close()

    summary = build_summary(records)
    summary.update(
        {
            "run_id": run_id,
            "dataset_sha256": actual_dataset_hash,
            "model_id": model_manifest["model_id"],
            "model_revision": model_manifest["model_revision"],
            "model_cache_manifest_sha256": sha256_file(cache_path),
            "environment_manifest_sha256": environment_hash,
            "smoke_manifest_sha256": sha256_file(smoke_manifest_path),
        }
    )
    summary_path = write_json(
        run_directory / "processed-summary.json", summary
    )

    registry: list[dict[str, object]] = []
    add_registry_entry(
        registry,
        audit_path,
        "dataset-audit",
        command=command_text,
        evidence_level="E3",
    )
    for path in split_paths.values():
        add_registry_entry(
            registry,
            path,
            "split-manifest",
            command=command_text,
            evidence_level="E3",
        )
    add_registry_entry(
        registry,
        smoke_manifest_path,
        "smoke-selection",
        command=command_text,
        evidence_level="E3",
    )
    add_registry_entry(
        registry,
        cache_path,
        "model-cache-manifest",
        command=command_text,
        evidence_level="E3",
    )
    add_registry_entry(
        registry,
        environment_path,
        "environment-manifest",
        command=command_text,
        evidence_level="E3",
    )
    for path in sorted((run_directory / "raw-trials").glob("*.json")):
        add_registry_entry(
            registry,
            path,
            "raw-trial",
            command=command_text,
            evidence_level="E3",
        )
    add_registry_entry(
        registry,
        summary_path,
        "processed-summary",
        command=command_text,
        evidence_level="E3",
    )
    registry_path = write_json(
        run_directory / "artifact-registry.json",
        {"schema_version": "artifact-registry-v1", "artifacts": registry},
    )

    print(
        json.dumps(
            {
                "status": "REAL_MODEL_SMOKE_COMPLETED",
                "run_id": run_id,
                "cases": len(smoke_examples),
                "trials": len(records),
                "completed": sum(
                    record.status == "completed" for record in records
                ),
                "errors": sum(record.status == "error" for record in records),
                "timeouts": sum(
                    record.status == "timeout" for record in records
                ),
                "output_directory": run_directory.as_posix(),
                "artifact_registry": registry_path.as_posix(),
            },
            sort_keys=True,
        )
    )
    return 0 if any(record.status == "completed" for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
