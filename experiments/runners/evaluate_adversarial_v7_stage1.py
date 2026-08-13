from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v3 import pse_candidate_v3_rank
from personal_state_engine.candidate_v4 import pse_candidate_v4_rank
from personal_state_engine.candidate_v5 import pse_candidate_v5_rank
from personal_state_engine.candidate_v6 import pse_candidate_v6_rank
from personal_state_engine.zero_cost_baselines import bm25_rank, evaluate_cases, random_rank, recency_rank, tfidf_rank

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "benchmarks" / "algorithm-development" / "adversarial-v7-confirmatory"
DATASET = BENCH / "cases-v1.json"
MANIFEST = BENCH / "manifest-v1.json"
PROTOCOL = ROOT / "experiments" / "protocols" / "adversarial-v7-confirmatory-evaluation-v1.json"
STATS = ROOT / "experiments" / "protocols" / "adversarial-v7-statistics-v1.json"
V6_SOURCE = ROOT / "src" / "personal_state_engine" / "candidate_v6.py"
V6_CONFIG = ROOT / "experiments" / "configs" / "candidate-v6-v1.json"

EXPECTED_DATASET_SHA256 = "77f2113fdf67001c53a31f0d9eff4ecac7e71564335ab9a505665b44a05546cd"
EXPECTED_V6_SOURCE_SHA256 = "c540056c6f30f0145ab8ef8c10be3abcae2ed24e6a087a2d9a3531bc5e545325"
EXPECTED_V6_CONFIG_SHA256 = "067bfa64d97bf2eb1f7208082c36d202118a0e50a2414fc345bf328f83cab5b1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if manifest["status"] != "FROZEN_BEFORE_ANY_SYSTEM_EXECUTION":
        raise SystemExit("adversarial-v7 benchmark not frozen")
    if sha256(DATASET) != EXPECTED_DATASET_SHA256 or manifest["dataset_sha256"] != EXPECTED_DATASET_SHA256:
        raise SystemExit("adversarial-v7 dataset identity mismatch")
    if sha256(PROTOCOL) != manifest["evaluation_protocol_sha256"]:
        raise SystemExit("adversarial-v7 evaluation protocol identity mismatch")
    if sha256(STATS) != manifest["statistics_protocol_sha256"]:
        raise SystemExit("adversarial-v7 statistics protocol identity mismatch")
    if sha256(V6_SOURCE) != EXPECTED_V6_SOURCE_SHA256 or manifest["candidate_v6_source_sha256"] != EXPECTED_V6_SOURCE_SHA256:
        raise SystemExit("Candidate-v6 frozen source identity mismatch")
    if sha256(V6_CONFIG) != EXPECTED_V6_CONFIG_SHA256 or manifest["candidate_v6_config_sha256"] != EXPECTED_V6_CONFIG_SHA256:
        raise SystemExit("Candidate-v6 frozen config identity mismatch")

    data = json.loads(DATASET.read_text(encoding="utf-8"))
    cases = data["cases"]
    if len(cases) != 90 or len({case["id"] for case in cases}) != 90:
        raise SystemExit("adversarial-v7 requires 90 unique cases")
    if sum(bool(case["relevant_memory_ids"]) for case in cases) != 60:
        raise SystemExit("adversarial-v7 answerable count mismatch")

    systems: dict[str, Callable[[dict[str, Any], int], list[str]]] = {
        "candidate-v2-frozen": pse_candidate_v2_rank,
        "candidate-v3-frozen": pse_candidate_v3_rank,
        "candidate-v4-frozen": pse_candidate_v4_rank,
        "candidate-v5-frozen": pse_candidate_v5_rank,
        "candidate-v6-frozen": pse_candidate_v6_rank,
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
        }

    v2 = results["candidate-v2-frozen"]
    v6 = results["candidate-v6-frozen"]
    random_m = results["random-deterministic"]["metrics"]
    recency_m = results["recency"]["metrics"]
    rule = protocol["stage1"]["discrimination_rule"]
    mrr_gap = v2["metrics"]["MRR"] - max(random_m["MRR"], recency_m["MRR"])
    r1_gap = v2["metrics"]["recall@1"] - max(random_m["recall@1"], recency_m["recall@1"])
    discrimination_checks = {
        "mrr_gap": mrr_gap >= rule["candidate_v2_mrr_gap_over_max_random_recency_minimum"] - 1e-12,
        "recall_at_1_gap": r1_gap >= rule["candidate_v2_recall_at_1_gap_over_max_random_recency_minimum"] - 1e-12,
    }
    discrimination_pass = all(discrimination_checks.values())

    guard = protocol["stage1"]["candidate_v6_selection_guardrails"]
    d6 = v6["decision_metrics"]
    d2 = v2["decision_metrics"]
    checks = {
        "abstention_accuracy": d6["abstention_accuracy"] >= guard["minimum_abstention_accuracy"] - 1e-12,
        "false_retrieval_rate": d6["false_retrieval_rate"] <= guard["maximum_false_retrieval_rate"] + 1e-12,
        "false_retrieval_reduction_vs_v2": (d2["false_retrieval_rate"] - d6["false_retrieval_rate"]) >= guard["minimum_absolute_false_retrieval_reduction_vs_candidate_v2"] - 1e-12,
        "false_abstention_rate": d6["false_abstention_rate"] <= guard["maximum_false_abstention_rate"] + 1e-12,
        "answerable_recall": d6["answerable_recall"] >= guard["minimum_answerable_recall"] - 1e-12,
        "mrr_preservation": (v2["metrics"]["MRR"] - v6["metrics"]["MRR"]) <= guard["maximum_mrr_deficit_vs_candidate_v2"] + 1e-12,
        "recall_at_1_preservation": (v2["metrics"]["recall@1"] - v6["metrics"]["recall@1"]) <= guard["maximum_recall_at_1_deficit_vs_candidate_v2"] + 1e-12,
        "recall_at_3_preservation": (v2["metrics"]["recall@3"] - v6["metrics"]["recall@3"]) <= guard["maximum_recall_at_3_deficit_vs_candidate_v2"] + 1e-12,
        "recall_at_5_preservation": (v2["metrics"]["recall@5"] - v6["metrics"]["recall@5"]) <= guard["maximum_recall_at_5_deficit_vs_candidate_v2"] + 1e-12,
    }
    guardrails_pass = all(checks.values())
    stage2_authorized = discrimination_pass and guardrails_pass

    payload = {
        "schema_version": "adversarial-v7-stage1-results-v1",
        "stage": "STAGE1_CHEAP_SYSTEMS_ONLY",
        "dataset_sha256": EXPECTED_DATASET_SHA256,
        "manifest_sha256": sha256(MANIFEST),
        "protocol_sha256": sha256(PROTOCOL),
        "statistics_protocol_sha256": sha256(STATS),
        "candidate_v6_source_sha256": EXPECTED_V6_SOURCE_SHA256,
        "candidate_v6_config_sha256": EXPECTED_V6_CONFIG_SHA256,
        "systems": results,
        "benchmark_discrimination": {
            "verdict": "PASS" if discrimination_pass else "FAIL",
            "checks": discrimination_checks,
            "candidate_v2_mrr_gap_over_max_random_recency": mrr_gap,
            "candidate_v2_recall_at_1_gap_over_max_random_recency": r1_gap,
        },
        "candidate_v6_frozen_guardrails": {
            "verdict": "PASS" if guardrails_pass else "FAIL",
            "checks": checks,
            "mrr_deficit_vs_candidate_v2": v2["metrics"]["MRR"] - v6["metrics"]["MRR"],
            "recall_at_1_deficit_vs_candidate_v2": v2["metrics"]["recall@1"] - v6["metrics"]["recall@1"],
            "recall_at_3_deficit_vs_candidate_v2": v2["metrics"]["recall@3"] - v6["metrics"]["recall@3"],
            "recall_at_5_deficit_vs_candidate_v2": v2["metrics"]["recall@5"] - v6["metrics"]["recall@5"],
            "absolute_false_retrieval_reduction_vs_candidate_v2": d2["false_retrieval_rate"] - d6["false_retrieval_rate"],
        },
        "stage2_exact_a_mem_authorized": stage2_authorized,
        "integrity": {
            "candidate_v6_changed_after_freeze": False,
            "benchmark_changed_after_freeze": False,
            "candidate_v6_protected_validation_rerun": False,
            "sealed_final_accessed": False,
            "new_monetary_cost_usd": 0.0,
            "paid_api": False,
            "paid_gpu": False,
        },
        "claim_boundary": "Stage-1 cannot establish exact A-MEM non-inferiority, superiority, parity, equivalence, Gate E completion, or sealed-final readiness."
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "benchmark_discrimination": payload["benchmark_discrimination"],
        "candidate_v6_guardrails": payload["candidate_v6_frozen_guardrails"],
        "candidate_v2": {"metrics": v2["metrics"], "decision_metrics": d2},
        "candidate_v6": {"metrics": v6["metrics"], "decision_metrics": d6},
        "stage2_exact_a_mem_authorized": stage2_authorized,
    }, indent=2, sort_keys=True))
    return 0 if stage2_authorized else 2


if __name__ == "__main__":
    raise SystemExit(main())
