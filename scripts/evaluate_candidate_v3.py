#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v3 import pse_candidate_v3_rank
from personal_state_engine.zero_cost_baselines import evaluate_cases

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_SPLITS = {
    "development": ROOT / "benchmarks/algorithm-development/abstention-dev-v1/development.json",
    "validation": ROOT / "benchmarks/algorithm-development/abstention-dev-v1/validation.json",
}
PROTOCOL = ROOT / "experiments/protocols/candidate-v3-design-preregistration-v1.json"
SOURCE = ROOT / "src/personal_state_engine/candidate_v3.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decision_metrics(cases: list[dict[str, Any]], ranker: Callable[[dict[str, Any], int], list[str]]) -> dict[str, Any]:
    answerable = [case for case in cases if case["relevant_memory_ids"]]
    no_evidence = [case for case in cases if not case["relevant_memory_ids"]]
    false_abstentions = sum(not ranker(case, 5) for case in answerable)
    false_retrievals = sum(bool(ranker(case, 5)) for case in no_evidence)
    return {
        "answerable_case_count": len(answerable),
        "no_evidence_case_count": len(no_evidence),
        "false_abstention_rate": false_abstentions / len(answerable) if answerable else None,
        "false_retrieval_rate": false_retrievals / len(no_evidence) if no_evidence else None,
        "abstention_accuracy": 1.0 - (false_retrievals / len(no_evidence)) if no_evidence else None,
    }


def evaluate(split: str) -> dict[str, Any]:
    dataset = ALLOWED_SPLITS[split]
    payload = json.loads(dataset.read_text(encoding="utf-8"))
    cases = payload["cases"]
    systems = {
        "pse_candidate_v2_frozen": pse_candidate_v2_rank,
        "pse_candidate_v3": pse_candidate_v3_rank,
    }
    results: dict[str, Any] = {}
    for name, ranker in systems.items():
        retrieval = evaluate_cases(cases, ranker, 5)
        results[name] = {
            **retrieval,
            "decision_metrics": decision_metrics(cases, ranker),
        }
    return {
        "schema_version": "candidate-v3-evaluation-v1",
        "split": split,
        "dataset_path": str(dataset.relative_to(ROOT)),
        "dataset_sha256": sha256(dataset),
        "protocol_path": str(PROTOCOL.relative_to(ROOT)),
        "protocol_sha256": sha256(PROTOCOL),
        "candidate_v3_source_path": str(SOURCE.relative_to(ROOT)),
        "candidate_v3_source_sha256": sha256(SOURCE),
        "candidate_v2_freeze_commit": "d627f61d0888306a97f3ef0b78aa29dc00c444bb",
        "selection_data": "development only" if split == "development" else "one-time frozen validation; no retuning permitted",
        "results": results,
        "integrity": {
            "candidate_v2_changed": False,
            "sealed_final_accessed": False,
            "new_monetary_cost_usd": 0.0,
        },
        "claim_boundary": "Non-sealed candidate-v3 development/validation evidence only; not parity, superiority, Gate E completion, or independent reproduction evidence.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=sorted(ALLOWED_SPLITS), required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = evaluate(args.split)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
