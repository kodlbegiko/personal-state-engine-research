#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v3 import pse_candidate_v3_rank
from personal_state_engine.candidate_v4 import pse_candidate_v4_rank
from personal_state_engine.zero_cost_baselines import (
    bm25_rank,
    evaluate_cases,
    pse_candidate_v1_rank,
    pse_current_rank,
    random_rank,
    recency_rank,
    tfidf_rank,
)

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "benchmarks/algorithm-development/adversarial-v6-confirmatory/cases-v1.json"
MANIFEST = ROOT / "benchmarks/algorithm-development/adversarial-v6-confirmatory/manifest-v1.json"
PROTOCOL = ROOT / "experiments/protocols/adversarial-v6-confirmatory-evaluation-v1.json"
STATS = ROOT / "experiments/protocols/adversarial-v6-statistics-v1.json"
V4_SOURCE = ROOT / "src/personal_state_engine/candidate_v4.py"
V4_CONFIG = ROOT / "experiments/protocols/candidate-v4-config-v1.json"
EXPECTED = {
    DATASET: "d5ff2fa4c51ebf09c42c710cd6a8bcf8445060858abf07ed1b34a7ac940471b0",
    V4_SOURCE: "b57af79b3ef91497a4d3df373a990f0daa76a21c4daf87c7dd27f1c258c6d344",
    V4_CONFIG: "a6341817ed382423a4d48d5df890765bb59f887655f16bd0e0647b89e3379606",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_identities() -> None:
    for path, expected in EXPECTED.items():
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"identity mismatch: {path.relative_to(ROOT)} {actual} != {expected}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["dataset_sha256"] != EXPECTED[DATASET]:
        raise RuntimeError("manifest dataset SHA mismatch")
    if manifest["status"] != "FROZEN_BEFORE_ANY_SYSTEM_EXECUTION":
        raise RuntimeError("v6 manifest is not frozen")


def decision_metrics(cases: list[dict[str, Any]], ranker: Callable[[dict[str, Any], int], list[str]]) -> dict[str, Any]:
    answerable = [case for case in cases if case["relevant_memory_ids"]]
    no_evidence = [case for case in cases if not case["relevant_memory_ids"]]
    false_abstentions = [case["id"] for case in answerable if not ranker(case, 5)]
    false_retrievals = [case["id"] for case in no_evidence if ranker(case, 5)]
    return {
        "answerable_case_count": len(answerable),
        "no_evidence_case_count": len(no_evidence),
        "false_abstention_count": len(false_abstentions),
        "false_abstention_case_ids": false_abstentions,
        "false_abstention_rate": len(false_abstentions) / len(answerable),
        "answerable_recall": 1.0 - len(false_abstentions) / len(answerable),
        "false_retrieval_count": len(false_retrievals),
        "false_retrieval_case_ids": false_retrievals,
        "false_retrieval_rate": len(false_retrievals) / len(no_evidence),
        "abstention_accuracy": 1.0 - len(false_retrievals) / len(no_evidence),
    }


def category_decisions(cases: list[dict[str, Any]], ranker: Callable[[dict[str, Any], int], list[str]]) -> dict[str, Any]:
    output: dict[str, dict[str, int]] = {}
    for case in cases:
        row = output.setdefault(case["category"], {"cases": 0, "retrieved": 0, "abstained": 0})
        row["cases"] += 1
        if ranker(case, 5):
            row["retrieved"] += 1
        else:
            row["abstained"] += 1
    return dict(sorted(output.items()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verify_identities()
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    cases = data["cases"]
    if len(cases) != 90 or len({case["id"] for case in cases}) != 90:
        raise RuntimeError("v6 case-count or uniqueness failure")

    systems: dict[str, Callable[[dict[str, Any], int], list[str]]] = {
        "pse_current": pse_current_rank,
        "candidate-v1": pse_candidate_v1_rank,
        "candidate-v2-frozen": pse_candidate_v2_rank,
        "candidate-v3-frozen": pse_candidate_v3_rank,
        "candidate-v4-frozen": pse_candidate_v4_rank,
        "bm25-local": bm25_rank,
        "tfidf-local": tfidf_rank,
        "random-deterministic": random_rank,
        "recency": recency_rank,
    }
    results: dict[str, Any] = {}
    for name, ranker in systems.items():
        results[name] = {
            **evaluate_cases(cases, ranker, 5),
            "decision_metrics": decision_metrics(cases, ranker),
            "category_decisions": category_decisions(cases, ranker),
        }

    v2 = results["candidate-v2-frozen"]
    v4 = results["candidate-v4-frozen"]
    random_m = results["random-deterministic"]["metrics"]
    recency_m = results["recency"]["metrics"]
    rule = protocol["stage1"]["discrimination_rule"]
    mrr_gap = v2["metrics"]["MRR"] - max(random_m["MRR"], recency_m["MRR"])
    r1_gap = v2["metrics"]["recall@1"] - max(random_m["recall@1"], recency_m["recall@1"])
    discrimination_checks = {
        "mrr_gap": mrr_gap >= rule["candidate_v2_mrr_gap_over_max_random_recency_minimum"],
        "recall_at_1_gap": r1_gap >= rule["candidate_v2_recall_at_1_gap_over_max_random_recency_minimum"],
    }
    discrimination = "PASS" if all(discrimination_checks.values()) else "BENCHMARK_DISCRIMINATION_FAILURE"

    guard = protocol["candidate_v4_selection_guardrails"]
    d4 = v4["decision_metrics"]
    d2 = v2["decision_metrics"]
    v4_checks = {
        "abstention_accuracy": d4["abstention_accuracy"] >= guard["minimum_abstention_accuracy"],
        "false_retrieval_rate": d4["false_retrieval_rate"] <= guard["maximum_false_retrieval_rate"],
        "false_retrieval_reduction_vs_v2": (d2["false_retrieval_rate"] - d4["false_retrieval_rate"]) >= guard["minimum_absolute_false_retrieval_reduction_vs_candidate_v2"],
        "false_abstention_rate": d4["false_abstention_rate"] <= guard["maximum_false_abstention_rate"],
        "answerable_recall": d4["answerable_recall"] >= guard["minimum_answerable_recall"],
        "mrr_preservation": (v2["metrics"]["MRR"] - v4["metrics"]["MRR"]) <= guard["maximum_mrr_deficit_vs_candidate_v2"],
        "recall_at_1_preservation": (v2["metrics"]["recall@1"] - v4["metrics"]["recall@1"]) <= guard["maximum_recall_at_1_deficit_vs_candidate_v2"],
        "recall_at_3_preservation": (v2["metrics"]["recall@3"] - v4["metrics"]["recall@3"]) <= guard["maximum_recall_at_3_deficit_vs_candidate_v2"],
        "recall_at_5_preservation": (v2["metrics"]["recall@5"] - v4["metrics"]["recall@5"]) <= guard["maximum_recall_at_5_deficit_vs_candidate_v2"],
    }

    payload = {
        "schema_version": "adversarial-v6-stage1-results-v1",
        "stage": "STAGE1_CHEAP_SYSTEMS_ONLY",
        "dataset_sha256": EXPECTED[DATASET],
        "dataset_freeze_commit": "eedf72da4d73abcb6febe377e66794f1a6179bca",
        "protocol_sha256": sha256(PROTOCOL),
        "statistics_protocol_sha256": sha256(STATS),
        "candidate_v4_freeze_commit": "e6780204686d3de526905eca8f2778c2510b7876",
        "candidate_v4_source_sha256": EXPECTED[V4_SOURCE],
        "candidate_v4_config_sha256": EXPECTED[V4_CONFIG],
        "systems": results,
        "benchmark_discrimination": {
            "verdict": discrimination,
            "checks": discrimination_checks,
            "candidate_v2_mrr_gap_over_max_random_recency": mrr_gap,
            "candidate_v2_recall_at_1_gap_over_max_random_recency": r1_gap,
            "exact_a_mem_authorized": discrimination == "PASS",
        },
        "candidate_v4_frozen_guardrails": {
            "verdict": "PASS" if all(v4_checks.values()) else "FAIL",
            "checks": v4_checks,
        },
        "integrity": {
            "candidate_v2_changed": False,
            "candidate_v3_changed": False,
            "candidate_v4_changed_after_freeze": False,
            "benchmark_changed_after_freeze": False,
            "sealed_final_content_accessed_by_stage1": False,
            "new_monetary_cost_usd": 0.0,
        },
        "claim_boundary": "Stage-1 establishes benchmark discrimination and frozen cheap-system metrics only. It cannot establish Gate E completion, A-MEM comparison, parity, superiority, equivalence or non-inferiority.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "benchmark_discrimination": payload["benchmark_discrimination"],
        "candidate_v4_guardrails": payload["candidate_v4_frozen_guardrails"],
        "candidate_v2": {"metrics": v2["metrics"], "decision_metrics": d2},
        "candidate_v4": {"metrics": v4["metrics"], "decision_metrics": d4},
        "random": random_m,
        "recency": recency_m,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
