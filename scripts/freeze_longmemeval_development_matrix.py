#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_smoke_module() -> Any:
    path = Path(__file__).with_name("run_longmemeval_e3_smoke.py")
    spec = importlib.util.spec_from_file_location("pse_e3_smoke", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load run_longmemeval_e3_smoke.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hash_rank(seed: str, case_id: str) -> str:
    return hashlib.sha256(f"{seed}|{case_id}".encode("utf-8")).hexdigest()


def select_cases(examples: list[Any], protocol: dict[str, Any]) -> list[Any]:
    selection = protocol["selection"]
    seed = str(selection["selection_seed"])
    targets = {str(k): int(v) for k, v in selection["question_type_targets"].items()}
    required_total = int(protocol["target_case_count"])
    if sum(targets.values()) != required_total:
        raise RuntimeError("question_type_targets must sum to target_case_count")

    by_type: dict[str, list[Any]] = defaultdict(list)
    for example in examples:
        by_type[example.question_type].append(example)
    for question_type, target in targets.items():
        if len(by_type[question_type]) < target:
            raise RuntimeError(f"insufficient cases for {question_type}: {len(by_type[question_type])} < {target}")
        by_type[question_type].sort(key=lambda row: (hash_rank(seed, row.question_id), row.question_id))

    selected: list[Any] = []
    selected_ids: set[str] = set()
    remaining = dict(targets)
    minimum_abstention = int(selection["minimum_abstention_cases"])
    abstention_by_type = {
        question_type: [row for row in rows if row.is_abstention]
        for question_type, rows in by_type.items()
    }
    type_order = sorted(targets, key=lambda value: hash_rank(seed + "|types", value))
    while sum(row.is_abstention for row in selected) < minimum_abstention:
        progressed = False
        for question_type in type_order:
            if remaining[question_type] <= 0:
                continue
            candidate = next(
                (row for row in abstention_by_type[question_type] if row.question_id not in selected_ids),
                None,
            )
            if candidate is None:
                continue
            selected.append(candidate)
            selected_ids.add(candidate.question_id)
            remaining[question_type] -= 1
            progressed = True
            if sum(row.is_abstention for row in selected) >= minimum_abstention:
                break
        if not progressed:
            raise RuntimeError("unable to satisfy minimum abstention quota")

    for question_type in sorted(targets):
        for candidate in by_type[question_type]:
            if remaining[question_type] <= 0:
                break
            if candidate.question_id in selected_ids:
                continue
            selected.append(candidate)
            selected_ids.add(candidate.question_id)
            remaining[question_type] -= 1

    if any(remaining.values()) or len(selected) != required_total:
        raise RuntimeError(f"selection incomplete: remaining={remaining}, selected={len(selected)}")
    return sorted(selected, key=lambda row: row.question_id)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze the preregistered LongMemEval development matrix subset without model inference.")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--parent-split-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    from personal_state_engine.longmemeval import load_longmemeval

    args = parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    source_manifest = json.loads(args.source_manifest.read_text(encoding="utf-8"))
    parent_manifest = json.loads(args.parent_split_manifest.read_text(encoding="utf-8"))
    if args.dataset.stat().st_size != int(source_manifest["expected_size_bytes"]):
        raise RuntimeError("dataset size mismatch")
    dataset_sha = sha256_file(args.dataset)
    if dataset_sha != source_manifest["expected_sha256"] or dataset_sha != protocol["dataset"]["sha256"]:
        raise RuntimeError("dataset hash mismatch")

    smoke = load_smoke_module()
    examples = load_longmemeval(args.dataset)
    splits = smoke.build_grouped_stratified_splits(examples, protocol["selection"]["parent_split_seed"])
    development = splits["development"]
    actual_parent_ids = [row.question_id for row in development]
    if actual_parent_ids != parent_manifest["case_ids"]:
        raise RuntimeError("recomputed development split differs from committed parent split")
    if smoke.canonical_sha256(actual_parent_ids) != parent_manifest["case_ids_sha256"]:
        raise RuntimeError("parent split case hash mismatch")

    selected = select_cases(development, protocol)
    fingerprints = [smoke.history_fingerprint(row) for row in selected]
    if len(set(fingerprints)) != len(fingerprints):
        raise RuntimeError("selected cases share a conversation-history fingerprint")

    records = [
        {
            "case_id": row.question_id,
            "question_type": row.question_type,
            "is_abstention": bool(row.is_abstention),
            "history_fingerprint": smoke.history_fingerprint(row),
            "selection_rank": hash_rank(protocol["selection"]["selection_seed"], row.question_id),
        }
        for row in selected
    ]
    payload: dict[str, Any] = {
        "schema_version": "longmemeval-development-matrix-manifest-v1",
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": sha256_file(args.protocol),
        "dataset_name": protocol["dataset"]["name"],
        "dataset_revision": protocol["dataset"]["revision"],
        "dataset_sha256": dataset_sha,
        "source_split": "development",
        "source_split_sha256": sha256_file(args.parent_split_manifest),
        "source_split_case_ids_sha256": parent_manifest["case_ids_sha256"],
        "selection_algorithm": protocol["selection"]["algorithm"],
        "selection_seed": protocol["selection"]["selection_seed"],
        "selection_code_commit": os.environ.get("GITHUB_SHA", "UNAVAILABLE"),
        "selection_timestamp": "2026-08-01T00:00:00Z",
        "forbidden_use": ["sealed-final", "post-result case selection", "reference-answer-driven selection"],
        "sample_count": len(records),
        "case_ids": [row["case_id"] for row in records],
        "case_ids_sha256": canonical_sha256([row["case_id"] for row in records]),
        "question_type_distribution": dict(sorted(Counter(row["question_type"] for row in records).items())),
        "abstention_case_count": sum(bool(row["is_abstention"]) for row in records),
        "history_fingerprint_sha256": canonical_sha256(sorted(fingerprints)),
        "history_isolation": "PASS",
        "sealed_final_accessed": False,
        "records": records,
    }
    payload["manifest_sha256"] = canonical_sha256(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "FROZEN", "output": args.output.as_posix(), "sample_count": len(records), "manifest_sha256": payload["manifest_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
