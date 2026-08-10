#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v4 import answerability_signature, pse_candidate_v4_rank
from personal_state_engine.zero_cost_baselines import evaluate_cases

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_SPLITS = {
    "development": ROOT / "benchmarks/algorithm-development/abstention-dev-v1/development.json",
    "validation": ROOT / "benchmarks/algorithm-development/abstention-dev-v1/validation.json",
}
PROTOCOL = ROOT / "experiments/protocols/candidate-v4-design-preregistration-v1.json"
SOURCE = ROOT / "src/personal_state_engine/candidate_v4.py"

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
        "answerable_recall": 1.0 - (false_abstentions / len(answerable)) if answerable else None,
        "false_retrieval_rate": false_retrievals / len(no_evidence) if no_evidence else None,
        "abstention_accuracy": 1.0 - (false_retrievals / len(no_evidence)) if no_evidence else None,
    }

def evaluate(split: str) -> dict[str, Any]:
    dataset = ALLOWED_SPLITS[split]
    payload = json.loads(dataset.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    cases = payload["cases"]
    systems = {"pse_candidate_v2_frozen": pse_candidate_v2_rank, "pse_candidate_v4": pse_candidate_v4_rank}
    results: dict[str, Any] = {}
    for name, ranker in systems.items():
        retrieval = evaluate_cases(cases, ranker, 5)
        results[name] = {**retrieval, "decision_metrics": decision_metrics(cases, ranker)}
    v2 = results["pse_candidate_v2_frozen"]["metrics"]
    v4 = results["pse_candidate_v4"]["metrics"]
    v4d = results["pse_candidate_v4"]["decision_metrics"]
    guardrails = protocol["development_acceptance" if split == "development" else "one_time_validation_acceptance"]
    checks = {
        "abstention_accuracy": v4d["abstention_accuracy"] >= guardrails["minimum_abstention_accuracy"],
        "false_retrieval_rate": v4d["false_retrieval_rate"] <= guardrails["maximum_false_retrieval_rate"],
        "false_abstention_rate": v4d["false_abstention_rate"] <= guardrails["maximum_false_abstention_rate"],
        "mrr_preservation": (v2["MRR"] - v4["MRR"]) <= guardrails["maximum_mrr_deficit_vs_candidate_v2"],
        "recall_at_1_preservation": (v2["recall@1"] - v4["recall@1"]) <= guardrails["maximum_recall_at_1_deficit_vs_candidate_v2"],
        "recall_at_3_preservation": (v2["recall@3"] - v4["recall@3"]) <= guardrails["maximum_recall_at_3_deficit_vs_candidate_v2"],
        "recall_at_5_preservation": (v2["recall@5"] - v4["recall@5"]) <= guardrails["maximum_recall_at_5_deficit_vs_candidate_v2"],
    }
    signatures = [{"case_id": case["id"], **answerability_signature(case, pse_candidate_v2_rank(case, 5))} for case in cases]
    return {
        "schema_version": "candidate-v4-evaluation-v1",
        "split": split,
        "dataset_path": str(dataset.relative_to(ROOT)),
        "dataset_sha256": sha256(dataset),
        "protocol_path": str(PROTOCOL.relative_to(ROOT)),
        "protocol_sha256": sha256(PROTOCOL),
        "candidate_v4_source_path": str(SOURCE.relative_to(ROOT)),
        "candidate_v4_source_sha256": sha256(SOURCE),
        "candidate_v2_freeze_commit": "d627f61d0888306a97f3ef0b78aa29dc00c444bb",
        "selection_data": "development only" if split == "development" else "one-time frozen validation; no retuning permitted",
        "results": results,
        "guardrail_checks": checks,
        "acceptance": "PASS" if all(checks.values()) else "FAIL",
        "answerability_signatures": signatures,
        "integrity": {"candidate_v2_changed": False, "candidate_v3_changed": False, "sealed_final_accessed": False, "new_monetary_cost_usd": 0.0},
        "claim_boundary": "Candidate-v4 development evidence only; v5 is historical diagnostic, not confirmatory." if split == "development" else "One-time frozen non-sealed Candidate-v4 validation only; not Gate E completion or parity evidence.",
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
