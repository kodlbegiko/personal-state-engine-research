#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import re
import subprocess
import sys
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Iterable, Sequence


class DevelopmentMatrixError(RuntimeError):
    pass


def load_smoke_module() -> Any:
    path = Path(__file__).with_name("run_longmemeval_e3_smoke.py")
    spec = importlib.util.spec_from_file_location("pse_e3_smoke", path)
    if spec is None or spec.loader is None:
        raise DevelopmentMatrixError("unable to load E3 support module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DevelopmentMatrixError(f"{path} must contain a JSON object")
    return value


def require_exact_revision(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise DevelopmentMatrixError(f"{field} must be an exact 40-hex revision")
    return value


def parse_judge_output(text: str) -> dict[str, object]:
    raw = text.strip()
    candidates = [raw]
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if match and match.group(0) != raw:
        candidates.append(match.group(0))
    last_error = "no JSON object"
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = str(exc)
            continue
        if not isinstance(value, dict):
            last_error = "judge output root is not an object"
            continue
        correct = value.get("correct")
        rationale = value.get("rationale")
        if not isinstance(correct, bool) or not isinstance(rationale, str) or not rationale.strip():
            last_error = "judge output requires boolean correct and non-blank rationale"
            continue
        return {
            "status": "VALID",
            "score": int(correct),
            "correct": correct,
            "rationale": rationale.strip(),
            "raw_text": text,
        }
    return {
        "status": "INVALID",
        "score": None,
        "correct": None,
        "rationale": None,
        "raw_text": text,
        "error": last_error,
    }


def semantic_judge(
    adapter: Any,
    answer_manifest: Any,
    *,
    case_id: str,
    question: str,
    reference: object,
    candidate: str | None,
    is_abstention: bool,
) -> dict[str, object]:
    from personal_state_engine.model_adapters import ModelRequest

    judge_manifest = replace(answer_manifest, seed=29, token_budget=96)
    system_prompt = (
        "You are a strict, blinded evaluator for a long-term-memory question answering benchmark. "
        "Decide whether the candidate answer is semantically correct relative to the reference answer. "
        "Accept equivalent concise wording. Reject answers that add a materially wrong fact. "
        "For an insufficient-information case, accept only an explicit uncertainty or unknown answer. "
        "Do not infer which system produced the answer. Return exactly one JSON object with keys "
        "correct (boolean) and rationale (short string)."
    )
    user_payload = {
        "question": question,
        "reference_answer": reference,
        "candidate_answer": candidate,
        "is_insufficient_information_case": is_abstention,
    }
    request = ModelRequest(
        request_id=f"judge:{case_id}:{uuid.uuid4()}",
        system_prompt=system_prompt,
        messages=(
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True),
            },
        ),
        manifest=judge_manifest,
    )
    started = time.time()
    try:
        response = adapter.complete(request)
    except Exception as exc:
        return {
            "status": "ERROR",
            "score": None,
            "correct": None,
            "rationale": None,
            "raw_text": None,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "latency_ms": max(0.0, (time.time() - started) * 1000),
            "usage": {},
        }
    parsed = parse_judge_output(response.text)
    parsed.update(
        {
            "request_id": response.request_id,
            "latency_ms": response.latency_ms,
            "usage": response.usage,
            "raw_response": response.raw,
            "prompt_version": "longmemeval-semantic-judge-v1",
            "baseline_identity_hidden": True,
            "role_isolation": True,
        }
    )
    return parsed


def exact_binomial_two_sided(successes: int, trials: int, p: float = 0.5) -> float | None:
    if trials <= 0:
        return None
    probability = lambda k: math.comb(trials, k) * (p**k) * ((1 - p) ** (trials - k))
    observed = probability(successes)
    return min(1.0, sum(probability(k) for k in range(trials + 1) if probability(k) <= observed + 1e-15))


def wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    if trials <= 0:
        return None, None
    phat = successes / trials
    denominator = 1 + z * z / trials
    center = (phat + z * z / (2 * trials)) / denominator
    half = z * math.sqrt((phat * (1 - phat) + z * z / (4 * trials)) / trials) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (float(ordered[middle - 1]) + float(ordered[middle])) / 2


def human_audit_evidence(example: Any) -> list[dict[str, object]]:
    answer_ids = set(example.answer_session_ids)
    return [
        {
            "session_id": session.session_id,
            "timestamp": session.timestamp,
            "turns": [
                {"role": turn.role, "content": turn.content}
                for turn in session.turns
            ],
        }
        for session in example.sessions
        if session.session_id in answer_ids
    ]


def build_human_audit_queue(examples: Sequence[Any], records: Sequence[Any]) -> tuple[dict[str, object], dict[str, object]]:
    by_case: dict[str, dict[str, Any]] = defaultdict(dict)
    for record in records:
        by_case[record.case_id][record.baseline_id] = record
    example_by_id = {example.question_id: example for example in examples}
    selected_ids = sorted(
        by_case,
        key=lambda case_id: hashlib.sha256(f"human-audit-v1|{case_id}".encode()).hexdigest(),
    )[:10]
    queue_rows = []
    key_rows = []
    for case_id in selected_ids:
        example = example_by_id[case_id]
        baseline_order = (
            ("EXT-B0", "EXT-B5")
            if int(hashlib.sha256(case_id.encode()).hexdigest(), 16) % 2 == 0
            else ("EXT-B5", "EXT-B0")
        )
        labels = {baseline_order[0]: "A", baseline_order[1]: "B"}
        answers: dict[str, object] = {}
        key_entry: dict[str, object] = {"case_id": case_id, "mapping": {}}
        for baseline, label in labels.items():
            record = by_case[case_id][baseline]
            answers[label] = {
                "candidate_answer": record.parsed_answer,
                "evaluator_score": record.evaluator_output.get("score") if record.evaluator_output else None,
                "evaluator_rationale": (
                    record.evaluator_output.get("semantic", {}).get("rationale")
                    if record.evaluator_output
                    else None
                ),
                "human_decision": None,
                "disagreement_category": None,
            }
            key_entry["mapping"][label] = baseline
        queue_rows.append(
            {
                "case_id": case_id,
                "question_type": example.question_type,
                "is_abstention": example.is_abstention,
                "question": example.question,
                "reference_answer": example.answer,
                "relevant_history": human_audit_evidence(example),
                "answers": answers,
                "audit_status": "PENDING_SINGLE_OPERATOR_BLINDED_AUDIT",
            }
        )
        key_rows.append(key_entry)
    return (
        {
            "schema_version": "human-audit-queue-v1",
            "sample_size": len(queue_rows),
            "selection": "deterministic hash-ranked 10 cases",
            "operator_status": "single-operator audit; not independent",
            "baseline_identity": "blinded in queue; mapping stored separately",
            "rows": queue_rows,
        },
        {
            "schema_version": "human-audit-key-v1",
            "warning": "Open only after human decisions are recorded.",
            "rows": key_rows,
        },
    )


def build_summary(examples: Sequence[Any], records: Sequence[Any]) -> dict[str, object]:
    example_by_id = {example.question_id: example for example in examples}
    by_baseline: dict[str, dict[str, Any]] = defaultdict(dict)
    for record in records:
        by_baseline[record.baseline_id][record.case_id] = record

    baseline_summary: dict[str, object] = {}
    for baseline, rows in sorted(by_baseline.items()):
        values = list(rows.values())
        valid_scores = [
            int(record.evaluator_output["score"])
            for record in values
            if record.evaluator_output and record.evaluator_output.get("score") is not None
        ]
        judge_tokens = sum(
            int(record.evaluator_output.get("semantic", {}).get("usage", {}).get("input_tokens", 0))
            + int(record.evaluator_output.get("semantic", {}).get("usage", {}).get("output_tokens", 0))
            for record in values
            if record.evaluator_output
        )
        baseline_summary[baseline] = {
            "trials": len(values),
            "completed": sum(record.status == "completed" for record in values),
            "errors": sum(record.status == "error" for record in values),
            "timeouts": sum(record.status == "timeout" for record in values),
            "valid_semantic_scores": len(valid_scores),
            "invalid_or_failed_judge_outputs": len(values) - len(valid_scores),
            "semantic_correct": sum(valid_scores),
            "semantic_accuracy": sum(valid_scores) / len(valid_scores) if valid_scores else None,
            "answer_input_tokens": sum(record.input_tokens for record in values),
            "answer_output_tokens": sum(record.output_tokens for record in values),
            "answer_total_tokens": sum(record.total_tokens for record in values),
            "judge_total_tokens": judge_tokens,
            "combined_total_tokens": sum(record.total_tokens for record in values) + judge_tokens,
            "median_answer_latency_ms": median([record.latency_ms for record in values]),
            "median_judge_latency_ms": median([
                float(record.evaluator_output.get("semantic", {}).get("latency_ms", 0.0))
                for record in values
                if record.evaluator_output
            ]),
            "storage_bytes": sum(record.storage_bytes for record in values),
            "estimated_monetary_cost": sum(record.estimated_cost or 0.0 for record in values),
        }

    paired_rows = []
    wins = losses = ties = unscored = 0
    type_stats: dict[str, Counter[str]] = defaultdict(Counter)
    retrieval = Counter()
    common_ids = sorted(set(by_baseline["EXT-B0"]).intersection(by_baseline["EXT-B5"]))
    for case_id in common_ids:
        b0 = by_baseline["EXT-B0"][case_id]
        b5 = by_baseline["EXT-B5"][case_id]
        b0_score = b0.evaluator_output.get("score") if b0.evaluator_output else None
        b5_score = b5.evaluator_output.get("score") if b5.evaluator_output else None
        difference = None if b0_score is None or b5_score is None else int(b5_score) - int(b0_score)
        if difference is None:
            unscored += 1
        elif difference > 0:
            wins += 1
        elif difference < 0:
            losses += 1
        else:
            ties += 1
        question_type = b0.question_type
        type_stats[question_type]["cases"] += 1
        if b0_score is not None:
            type_stats[question_type]["b0_correct"] += int(b0_score)
        if b5_score is not None:
            type_stats[question_type]["b5_correct"] += int(b5_score)
        example = example_by_id[case_id]
        evidence_ids = set(example.answer_session_ids)
        retrieved_ids = set(b5.retrieved_items)
        hit = bool(evidence_ids.intersection(retrieved_ids)) if evidence_ids else example.is_abstention
        retrieval["cases"] += 1
        retrieval["evidence_session_hit"] += int(hit)
        retrieval["retrieval_miss"] += int(not hit)
        retrieval["correct_retrieval_wrong_answer"] += int(hit and b5_score == 0)
        retrieval["wrong_retrieval_correct_answer"] += int((not hit) and b5_score == 1)
        retrieval["abstention_hallucination"] += int(example.is_abstention and b5_score == 0)
        paired_rows.append(
            {
                "case_id": case_id,
                "question_type": question_type,
                "is_abstention": example.is_abstention,
                "ext_b0_score": b0_score,
                "ext_b5_score": b5_score,
                "difference": difference,
                "evidence_session_ids": list(example.answer_session_ids),
                "retrieved_session_ids": list(b5.retrieved_items),
                "evidence_session_hit": hit,
            }
        )

    discordant = wins + losses
    mcnemar_p = exact_binomial_two_sided(wins, discordant)
    win_interval = wilson_interval(wins, discordant)
    b0 = baseline_summary.get("EXT-B0", {})
    b5 = baseline_summary.get("EXT-B5", {})
    additional_correct = int(b5.get("semantic_correct", 0)) - int(b0.get("semantic_correct", 0))
    incremental_tokens = int(b5.get("combined_total_tokens", 0)) - int(b0.get("combined_total_tokens", 0))
    incremental_latency = (
        (float(b5.get("median_answer_latency_ms") or 0) + float(b5.get("median_judge_latency_ms") or 0))
        - (float(b0.get("median_answer_latency_ms") or 0) + float(b0.get("median_judge_latency_ms") or 0))
    )
    incremental_storage = int(b5.get("storage_bytes", 0)) - int(b0.get("storage_bytes", 0))
    invalid_count = sum(
        1
        for record in records
        if not record.evaluator_output or record.evaluator_output.get("score") is None
    )
    return {
        "schema_version": "longmemeval-development-summary-v1",
        "evidence_label": "PREREGISTERED DEVELOPMENT MATRIX — E3 DEVELOPMENT EVIDENCE",
        "development_only": True,
        "case_count": len(common_ids),
        "trial_count": len(records),
        "baseline_summary": baseline_summary,
        "paired": {
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "unscored": unscored,
            "discordant_pairs": discordant,
            "mcnemar_exact_p_value": mcnemar_p,
            "ext_b5_win_rate_among_discordant": wins / discordant if discordant else None,
            "ext_b5_win_rate_wilson_95pct": list(win_interval),
            "rows": paired_rows,
        },
        "question_type_results": {key: dict(value) for key, value in sorted(type_stats.items())},
        "retrieval_diagnostics": {
            **dict(retrieval),
            "evidence_session_recall_at_k": retrieval["evidence_session_hit"] / retrieval["cases"] if retrieval["cases"] else None,
            "has_answer_used_for_ranking": False,
        },
        "evaluator": {
            "id": "qwen2.5-0.5b-semantic-judge-v1",
            "role_isolated_from_answer_request": True,
            "not_independent_model": True,
            "valid_output_count": len(records) - invalid_count,
            "invalid_output_count": invalid_count,
            "invalid_output_rate": invalid_count / len(records) if records else None,
            "formal_calibration_status": "PENDING_HUMAN_AUDIT",
        },
        "cost_effectiveness": {
            "additional_correct_answers": additional_correct,
            "incremental_combined_tokens": incremental_tokens,
            "incremental_median_latency_ms": incremental_latency,
            "incremental_storage_bytes": incremental_storage,
            "incremental_monetary_cost": float(b5.get("estimated_monetary_cost", 0.0)) - float(b0.get("estimated_monetary_cost", 0.0)),
            "tokens_per_additional_correct": incremental_tokens / additional_correct if additional_correct > 0 else None,
            "latency_ms_per_additional_correct": incremental_latency / additional_correct if additional_correct > 0 else None,
            "storage_bytes_per_additional_correct": incremental_storage / additional_correct if additional_correct > 0 else None,
            "monetary_cost_per_additional_correct": 0.0 if additional_correct > 0 else None,
            "undefined_ratio_reason": None if additional_correct > 0 else "No positive additional-correct denominator.",
        },
        "claim_limit": "Results cannot support parity, superiority, equivalence, non-inferiority, production readiness, security, or sealed external validity.",
    }


def add_registry_entry(
    registry: list[dict[str, object]],
    path: Path,
    artifact_type: str,
    *,
    command: str,
    code_commit: str,
    dataset_hash: str,
    split_hash: str,
    config_hash: str,
    model_manifest_hash: str,
    source_artifacts: Iterable[str] = (),
) -> None:
    registry.append(
        {
            "path": path.as_posix(),
            "artifact_type": artifact_type,
            "sha256": sha256_file(path),
            "status": "complete",
            "evidence_level": "E3",
            "code_commit": code_commit,
            "dataset_hash": dataset_hash,
            "split_hash": split_hash,
            "config_hash": config_hash,
            "model_manifest_hash": model_manifest_hash,
            "source_artifacts": list(source_artifacts),
            "generator_command": command,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the fixed 20-case LongMemEval EXT-B0/EXT-B5 development matrix.")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--model-manifest", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--matrix-config", type=Path, required=True)
    parser.add_argument("--model-server", type=Path, required=True)
    parser.add_argument("--cache-directory", type=Path, default=Path(".external-data/hf-cache"))
    parser.add_argument("--output-root", type=Path, default=Path("results/development-matrix"))
    return parser.parse_args()


def main() -> int:
    from personal_state_engine.external_trials import ExternalTrialConfig, execute_trial, write_immutable_trial
    from personal_state_engine.longmemeval import load_longmemeval
    from personal_state_engine.model_adapters import RunManifest

    args = parse_args()
    smoke = load_smoke_module()
    source = load_json(args.source_manifest)
    protocol = load_json(args.protocol)
    split_manifest = load_json(args.split_manifest)
    model = load_json(args.model_manifest)
    matrix = load_json(args.matrix_config)
    answer_manifest = RunManifest.from_json(args.run_manifest)

    dataset_hash = sha256_file(args.dataset)
    if args.dataset.stat().st_size != int(source["expected_size_bytes"]):
        raise DevelopmentMatrixError("dataset size differs from pinned manifest")
    if dataset_hash != source["expected_sha256"] or dataset_hash != protocol["dataset"]["sha256"]:
        raise DevelopmentMatrixError("dataset hash differs from pinned protocol")
    model_revision = require_exact_revision(model.get("model_revision"), field="model_revision")
    tokenizer_revision = require_exact_revision(model.get("tokenizer_revision"), field="tokenizer_revision")
    if model_revision != answer_manifest.model_version or model["model_id"] != answer_manifest.model_id:
        raise DevelopmentMatrixError("model and run manifests disagree")
    if split_manifest["sample_count"] != protocol["target_case_count"] or split_manifest["sample_count"] < protocol["minimum_case_count"]:
        raise DevelopmentMatrixError("split sample count violates protocol")
    if split_manifest.get("sealed_final_accessed") is not False:
        raise DevelopmentMatrixError("sealed-final access flag is not false")
    expected_self_hash = split_manifest.get("manifest_sha256")
    without_self = dict(split_manifest)
    without_self.pop("manifest_sha256", None)
    if expected_self_hash != canonical_sha256(without_self):
        raise DevelopmentMatrixError("split manifest self hash mismatch")

    all_examples = load_longmemeval(args.dataset)
    development = smoke.build_grouped_stratified_splits(all_examples, protocol["selection"]["parent_split_seed"])["development"]
    development_by_id = {example.question_id: example for example in development}
    selected = []
    for row in split_manifest["records"]:
        case_id = row["case_id"]
        if case_id not in development_by_id:
            raise DevelopmentMatrixError(f"selected case absent from development split: {case_id}")
        example = development_by_id[case_id]
        if row["question_type"] != example.question_type or bool(row["is_abstention"]) != example.is_abstention:
            raise DevelopmentMatrixError(f"selected case metadata mismatch: {case_id}")
        if row["history_fingerprint"] != smoke.history_fingerprint(example):
            raise DevelopmentMatrixError(f"selected case history fingerprint mismatch: {case_id}")
        selected.append(example)
    if [example.question_id for example in selected] != split_manifest["case_ids"]:
        raise DevelopmentMatrixError("record and case-id order differs")

    code_commit = os.environ.get("GITHUB_SHA", "UNAVAILABLE")
    run_id = f"development-matrix-{os.environ.get('GITHUB_RUN_ID', int(time.time()))}-attempt-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
    run_directory = args.output_root / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    command_text = "python scripts/run_longmemeval_development_matrix.py ..."

    environment = os.environ.copy()
    environment.update(
        {
            "PSE_MODEL_ID": model["model_id"],
            "PSE_MODEL_REVISION": model_revision,
            "PSE_MODEL_DTYPE": model["quantization"],
            "PSE_HF_CACHE": args.cache_directory.as_posix(),
        }
    )
    adapter = smoke.PersistentNodeAdapter(["node", args.model_server.as_posix()], environment)
    records = []
    try:
        cache_path = write_json(run_directory / "model-cache-manifest.json", smoke.cache_manifest(args.cache_directory))
        environment_payload = {
            "schema_version": "development-environment-manifest-v1",
            "platform": platform.platform(),
            "python": sys.version,
            "node": subprocess.run(["node", "--version"], capture_output=True, text=True, check=True).stdout.strip(),
            "cpu_count": os.cpu_count(),
            "machine": platform.machine(),
            "model_server_ready": adapter.ready,
            "model_cache_manifest_sha256": sha256_file(cache_path),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "github_sha": code_commit,
            "security_scope": model["security_scope"],
        }
        environment_path = write_json(run_directory / "environment-manifest.json", environment_payload)
        environment_hash = sha256_file(environment_path)

        screening_pool = [example for example in development if example.question_id not in set(split_manifest["case_ids"])]
        screening_cases = sorted(
            screening_pool,
            key=lambda example: hashlib.sha256(f"model-screen-v1|{example.question_id}".encode()).hexdigest(),
        )[:2]
        screening_rows = []
        for example in screening_cases:
            screening_config = ExternalTrialConfig(
                run_id=run_id + "-screen",
                dataset_name=protocol["dataset"]["name"],
                dataset_version=protocol["dataset"]["revision"],
                dataset_sha256=dataset_hash,
                split_name="development-screening",
                split_manifest_sha256=sha256_file(args.split_manifest),
                baseline_id="EXT-B0",
                baseline_version="external-baseline-v1",
                retrieval_item_limit=int(matrix["retrieval"]["k"]),
                retrieval_token_budget=int(matrix["retrieval"]["retrieval_token_budget"]),
                memory_token_budget=int(matrix["retrieval"]["memory_token_budget"]),
                code_commit=code_commit,
                environment_manifest_sha256=environment_hash,
            )
            screen = execute_trial(example, answer_manifest, screening_config, adapter)
            screening_rows.append(
                {
                    "case_id": example.question_id,
                    "status": screen.status,
                    "non_blank_output": bool(screen.parsed_answer and screen.parsed_answer.strip()),
                    "latency_ms": screen.latency_ms,
                    "error_type": screen.error_type,
                    "error_message": screen.error_message,
                }
            )
        screening_pass = all(row["status"] == "completed" and row["non_blank_output"] for row in screening_rows)
        screening_path = write_json(
            run_directory / "model-capability-screening.json",
            {
                "schema_version": "model-capability-screening-v1",
                "formal_matrix_overlap": False,
                "sealed_final_accessed": False,
                "selection_rule": "two deterministic hash-ranked non-matrix development cases",
                "selection_does_not_compare_baseline_advantage": True,
                "criteria": "runtime success and non-blank output only",
                "rows": screening_rows,
                "verdict": "PASS" if screening_pass else "FAIL",
                "limitation": "This screening proves executability, not absence of floor effect or competitive capability.",
            },
        )
        if not screening_pass:
            raise DevelopmentMatrixError("answer model failed predeclared non-overlapping capability screening")

        raw_directory = run_directory / "raw-trials"
        retrieval_k = int(matrix["retrieval"]["k"])
        for example in selected:
            ranked = smoke.bm25_scores(
                example.question,
                example.sessions,
                k=retrieval_k,
                k1=float(matrix["retrieval"]["k1"]),
                b=float(matrix["retrieval"]["b"]),
            )
            score_by_session = {session.session_id: score for session, score in ranked}
            for baseline in protocol["baseline_ids"]:
                config = ExternalTrialConfig(
                    run_id=run_id,
                    dataset_name=protocol["dataset"]["name"],
                    dataset_version=protocol["dataset"]["revision"],
                    dataset_sha256=dataset_hash,
                    split_name="development",
                    split_manifest_sha256=sha256_file(args.split_manifest),
                    baseline_id=baseline,
                    baseline_version="external-baseline-v1",
                    retrieval_item_limit=retrieval_k,
                    retrieval_token_budget=int(matrix["retrieval"]["retrieval_token_budget"]),
                    memory_token_budget=int(matrix["retrieval"]["memory_token_budget"]),
                    prompt_template_version="longmemeval-answer-v1",
                    evaluator_id=matrix["evaluator"]["id"],
                    evaluator_version="1",
                    code_commit=code_commit,
                    environment_manifest_sha256=environment_hash,
                )
                record = execute_trial(example, answer_manifest, config, adapter)
                deterministic = smoke.provisional_evaluate(
                    record.parsed_answer,
                    example.answer,
                    is_abstention=example.is_abstention,
                )
                semantic = semantic_judge(
                    adapter,
                    answer_manifest,
                    case_id=example.question_id,
                    question=example.question,
                    reference=example.answer,
                    candidate=record.parsed_answer,
                    is_abstention=example.is_abstention,
                )
                evaluator_output = {
                    "status": "SEMANTIC_SCORED" if semantic.get("score") is not None else "SEMANTIC_INVALID",
                    "score": semantic.get("score"),
                    "deterministic_diagnostic": deterministic,
                    "semantic": semantic,
                    "calibration_status": "PENDING_HUMAN_AUDIT",
                }
                retrieval_scores = tuple(score_by_session.get(session_id, 0.0) for session_id in record.retrieved_items)
                enriched = replace(
                    record,
                    tokenizer_id=model["tokenizer_id"],
                    tokenizer_revision=tokenizer_revision,
                    runtime_name=model["runtime_name"],
                    runtime_version=model["runtime_version"],
                    quantization=model["quantization"],
                    hardware=model["hardware"],
                    retrieval_scores=retrieval_scores,
                    retrieval_tokens=(
                        (record.raw_model_output or {}).get("usage", {}).get("retrieval_tokens", 0)
                        if baseline == "EXT-B5"
                        else 0
                    ),
                    evaluator_id=matrix["evaluator"]["id"],
                    evaluator_version="1",
                    evaluator_output=evaluator_output,
                    estimated_cost=0.0,
                )
                write_immutable_trial(enriched, raw_directory)
                records.append(enriched)
    finally:
        adapter.close()

    summary = build_summary(selected, records)
    summary.update(
        {
            "run_id": run_id,
            "dataset_sha256": dataset_hash,
            "protocol_sha256": sha256_file(args.protocol),
            "split_manifest_sha256": sha256_file(args.split_manifest),
            "model_manifest_sha256": sha256_file(args.model_manifest),
            "run_manifest_sha256": sha256_file(args.run_manifest),
            "matrix_config_sha256": sha256_file(args.matrix_config),
            "model_id": model["model_id"],
            "model_revision": model_revision,
            "environment_manifest_sha256": sha256_file(environment_path),
            "model_capability_screening_sha256": sha256_file(screening_path),
            "sealed_final_accessed": False,
        }
    )
    summary_path = write_json(run_directory / "processed-summary.json", summary)
    audit_queue, audit_key = build_human_audit_queue(selected, records)
    queue_path = write_json(run_directory / "human-audit-queue.json", audit_queue)
    key_path = write_json(run_directory / "human-audit-key.json", audit_key)

    registry: list[dict[str, object]] = []
    config_hash = sha256_file(args.matrix_config)
    model_hash = sha256_file(args.model_manifest)
    split_hash = sha256_file(args.split_manifest)
    for path, artifact_type, sources in (
        (cache_path, "model-cache-manifest", (args.model_manifest.as_posix(),)),
        (environment_path, "environment-manifest", (cache_path.as_posix(),)),
        (screening_path, "model-capability-screening", (args.model_manifest.as_posix(),)),
        (summary_path, "processed-summary", ("raw-trials",)),
        (queue_path, "human-audit-queue", (summary_path.as_posix(),)),
        (key_path, "human-audit-key", (queue_path.as_posix(),)),
    ):
        add_registry_entry(
            registry,
            path,
            artifact_type,
            command=command_text,
            code_commit=code_commit,
            dataset_hash=dataset_hash,
            split_hash=split_hash,
            config_hash=config_hash,
            model_manifest_hash=model_hash,
            source_artifacts=sources,
        )
    for path in sorted(raw_directory.glob("*.json")):
        add_registry_entry(
            registry,
            path,
            "raw-trial",
            command=command_text,
            code_commit=code_commit,
            dataset_hash=dataset_hash,
            split_hash=split_hash,
            config_hash=config_hash,
            model_manifest_hash=model_hash,
            source_artifacts=(args.split_manifest.as_posix(), args.model_manifest.as_posix()),
        )
    registry_path = write_json(
        run_directory / "artifact-registry.json",
        {
            "schema_version": "artifact-registry-v2",
            "run_id": run_id,
            "artifact_count": len(registry),
            "artifacts": registry,
        },
    )
    print(
        json.dumps(
            {
                "status": "DEVELOPMENT_MATRIX_COMPLETED",
                "run_id": run_id,
                "cases": len(selected),
                "trials": len(records),
                "completed": sum(record.status == "completed" for record in records),
                "errors": sum(record.status == "error" for record in records),
                "timeouts": sum(record.status == "timeout" for record in records),
                "output_directory": run_directory.as_posix(),
                "artifact_registry": registry_path.as_posix(),
            },
            sort_keys=True,
        )
    )
    return 0 if len(records) == 40 else 1


if __name__ == "__main__":
    raise SystemExit(main())
