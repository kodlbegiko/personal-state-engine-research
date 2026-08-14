#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


class ContractError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError(f"{path} must contain a JSON object")
    return value


def verify(run_directory: Path) -> dict[str, object]:
    if not run_directory.is_dir():
        raise ContractError(f"run directory does not exist: {run_directory}")
    summary = load_json(run_directory / "processed-summary.json")
    registry = load_json(run_directory / "artifact-registry.json")
    queue = load_json(run_directory / "human-audit-queue.json")
    key = load_json(run_directory / "human-audit-key.json")
    raw_paths = sorted((run_directory / "raw-trials").glob("*.json"))
    if len(raw_paths) != 40:
        raise ContractError(f"expected 40 raw trials, found {len(raw_paths)}")
    rows = [load_json(path) for path in raw_paths]

    trial_ids = [row["trial_id"] for row in rows]
    request_ids = [row["request_id"] for row in rows]
    if len(set(trial_ids)) != len(trial_ids):
        raise ContractError("duplicate trial_id")
    if len(set(request_ids)) != len(request_ids):
        raise ContractError("duplicate request_id")
    if any(int(row.get("attempt_number", 0)) < 1 for row in rows):
        raise ContractError("invalid attempt number")

    by_baseline: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_baseline[row["baseline_id"]].append(row)
    if set(by_baseline) != {"EXT-B0", "EXT-B5"}:
        raise ContractError(f"unexpected baselines: {sorted(by_baseline)}")
    if any(len(by_baseline[baseline]) != 20 for baseline in by_baseline):
        raise ContractError("each baseline must contain exactly 20 trials")
    b0_cases = {row["case_id"] for row in by_baseline["EXT-B0"]}
    b5_cases = {row["case_id"] for row in by_baseline["EXT-B5"]}
    if b0_cases != b5_cases or len(b0_cases) != 20:
        raise ContractError("paired case sets differ")

    for row in by_baseline["EXT-B0"]:
        reconstruction = row["raw_prompt_or_reconstruction_fields"]
        if row["retrieved_items"] or reconstruction.get("history") or int(row.get("retrieval_tokens", -1)) != 0:
            raise ContractError(f"EXT-B0 history leakage: {row['trial_id']}")
    for row in by_baseline["EXT-B5"]:
        if not row["retrieved_items"]:
            raise ContractError(f"EXT-B5 retrieval trace absent: {row['trial_id']}")
        if len(row["retrieved_items"]) != len(row["retrieval_scores"]):
            raise ContractError(f"EXT-B5 retrieval score mismatch: {row['trial_id']}")

    expected = {}
    for baseline, baseline_rows in by_baseline.items():
        valid_scores = [
            int(row["evaluator_output"]["score"])
            for row in baseline_rows
            if row.get("evaluator_output") and row["evaluator_output"].get("score") is not None
        ]
        expected[baseline] = {
            "trials": len(baseline_rows),
            "completed": sum(row["status"] == "completed" for row in baseline_rows),
            "errors": sum(row["status"] == "error" for row in baseline_rows),
            "timeouts": sum(row["status"] == "timeout" for row in baseline_rows),
            "valid_semantic_scores": len(valid_scores),
            "semantic_correct": sum(valid_scores),
        }
    for baseline, values in expected.items():
        recorded = summary["baseline_summary"][baseline]
        for field, value in values.items():
            if recorded[field] != value:
                raise ContractError(f"summary tie-out failed: {baseline}.{field}")

    artifacts = registry.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != int(registry.get("artifact_count", -1)):
        raise ContractError("registry artifact count mismatch")
    registered_paths = set()
    for artifact in artifacts:
        path = Path(artifact["path"])
        if not path.exists():
            raise ContractError(f"registered path missing: {path}")
        if sha256_file(path) != artifact["sha256"]:
            raise ContractError(f"registered hash mismatch: {path}")
        registered_paths.add(path.resolve())
    if not all(path.resolve() in registered_paths for path in raw_paths):
        raise ContractError("not every raw trial is registered")

    if int(queue.get("sample_size", 0)) != 10 or len(queue.get("rows", [])) != 10:
        raise ContractError("human audit queue must contain 10 cases")
    if len(key.get("rows", [])) != 10:
        raise ContractError("human audit key must contain 10 mappings")
    if summary.get("sealed_final_accessed") is not False:
        raise ContractError("sealed-final access flag is not false")

    secret_pattern = re.compile(r"(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")
    for path in [*raw_paths, run_directory / "processed-summary.json", run_directory / "human-audit-queue.json"]:
        if secret_pattern.search(path.read_text(encoding="utf-8")):
            raise ContractError(f"possible secret detected in {path}")

    statuses = Counter(row["status"] for row in rows)
    return {
        "status": "PASS",
        "run_id": summary["run_id"],
        "cases": len(b0_cases),
        "trials": len(rows),
        "trial_ids_unique": True,
        "request_ids_unique": True,
        "b0_history_exclusion": "PASS",
        "b5_retrieval_trace": "PASS",
        "raw_to_summary_tie_out": "PASS",
        "registry_hashes": "PASS",
        "human_audit_queue": "PASS",
        "sealed_final_accessed": False,
        "statuses": dict(statuses),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a LongMemEval development matrix evidence directory.")
    parser.add_argument("run_directory", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(json.dumps(verify(args.run_directory), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
