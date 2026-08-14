#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from materialize_adversarial_v5 import materialize
from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v3 import pse_candidate_v3_rank
from personal_state_engine.zero_cost_baselines import (
    bm25_rank,
    evaluate_cases,
    pse_candidate_v1_rank,
    pse_current_rank,
    random_rank,
    recency_rank,
    tfidf_rank,
)

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "benchmarks/algorithm-development/adversarial-v5/case-specifications-v1.json"
EXPECTED_DATASET_SHA256 = "41313c3da5f49e87a4456686e90c4b6934c4c088685f31679cc639b66ecbf169"
EXPECTED_CANDIDATE_V3_SHA256 = "8e0ba9d818804d3f032f6e9f19d6768207a020dea9def52e78755cd7f4a38284"


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def decision_metrics(cases: list[dict[str, Any]], ranker: Callable[[dict[str, Any], int], list[str]]) -> dict[str, Any]:
    answerable = [c for c in cases if c["relevant_memory_ids"]]
    no_evidence = [c for c in cases if not c["relevant_memory_ids"]]
    false_abstentions = sum(not ranker(c, 5) for c in answerable)
    false_retrievals = sum(bool(ranker(c, 5)) for c in no_evidence)
    return {
        "answerable_case_count": len(answerable),
        "no_evidence_case_count": len(no_evidence),
        "false_abstention_rate": false_abstentions / len(answerable),
        "false_retrieval_rate": false_retrievals / len(no_evidence),
        "abstention_accuracy": 1.0 - false_retrievals / len(no_evidence),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-output", type=Path)
    args = parser.parse_args()

    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    dataset = materialize(spec)
    dataset_bytes = canonical_bytes(dataset)
    dataset_sha = hashlib.sha256(dataset_bytes).hexdigest()
    if dataset_sha != EXPECTED_DATASET_SHA256:
        raise SystemExit(f"v5 dataset hash mismatch: {dataset_sha}")
    source_sha = hashlib.sha256((ROOT / "src/personal_state_engine/candidate_v3.py").read_bytes()).hexdigest()
    if source_sha != EXPECTED_CANDIDATE_V3_SHA256:
        raise SystemExit(f"candidate-v3 hash mismatch: {source_sha}")

    cases = dataset["cases"]
    systems: dict[str, Callable[[dict[str, Any], int], list[str]]] = {
        "random": random_rank,
        "recency": recency_rank,
        "bm25_local": bm25_rank,
        "tfidf_local": tfidf_rank,
        "pse_current_reconstruction": pse_current_rank,
        "pse_candidate_v1": pse_candidate_v1_rank,
        "pse_candidate_v2_frozen": pse_candidate_v2_rank,
        "pse_candidate_v3_frozen": pse_candidate_v3_rank,
    }
    results = {}
    for name, ranker in systems.items():
        results[name] = evaluate_cases(cases, ranker, 5)
        results[name]["decision_metrics"] = decision_metrics(cases, ranker)

    frontier_names = ["pse_current_reconstruction", "pse_candidate_v1", "pse_candidate_v2_frozen", "pse_candidate_v3_frozen"]
    best_mrr = max(results[n]["metrics"]["MRR"] for n in frontier_names)
    best_r1 = max(results[n]["metrics"]["recall@1"] for n in frontier_names)
    gaps = {}
    discrimination_pass = True
    for baseline in ("random", "recency"):
        mrr_gap = best_mrr - results[baseline]["metrics"]["MRR"]
        r1_gap = best_r1 - results[baseline]["metrics"]["recall@1"]
        gaps[baseline] = {"mrr_gap": mrr_gap, "recall_at_1_gap": r1_gap}
        discrimination_pass = discrimination_pass and mrr_gap >= 0.15 and r1_gap >= 0.15

    output = {
        "schema_version": "adversarial-v5-stage1-results-v1",
        "dataset_sha256": dataset_sha,
        "case_count": len(cases),
        "answerable_case_count": sum(bool(c["relevant_memory_ids"]) for c in cases),
        "no_evidence_case_count": sum(not c["relevant_memory_ids"] for c in cases),
        "candidate_v3_freeze_commit": "30e4de6860ef90219bb539fb03913012c83cc2ee",
        "candidate_v3_source_sha256": source_sha,
        "candidate_v2_freeze_commit": "d627f61d0888306a97f3ef0b78aa29dc00c444bb",
        "results": results,
        "discrimination": {
            "best_frontier_mrr": best_mrr,
            "best_frontier_recall_at_1": best_r1,
            "gaps": gaps,
            "minimum_gap": 0.15,
            "status": "PASS" if discrimination_pass else "FAIL",
        },
        "integrity": {
            "candidate_v3_changed_after_freeze": False,
            "candidate_v2_changed": False,
            "sealed_final_accessed": False,
            "new_monetary_cost_usd": 0.0,
        },
        "claim_boundary": "Frozen non-sealed v5 Stage-1 evidence only. A-MEM is not executed here; no parity, superiority, Gate E completion, or independent reproduction claim follows from this file alone.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.dataset_output:
        args.dataset_output.parent.mkdir(parents=True, exist_ok=True)
        args.dataset_output.write_bytes(dataset_bytes)


if __name__ == "__main__":
    main()
