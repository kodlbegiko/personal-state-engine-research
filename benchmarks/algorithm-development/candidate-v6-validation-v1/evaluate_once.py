from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v3 import pse_candidate_v3_rank
from personal_state_engine.candidate_v4 import pse_candidate_v4_rank
from personal_state_engine.candidate_v5 import pse_candidate_v5_rank
from personal_state_engine.candidate_v6 import answerability_signature, pse_candidate_v6_rank
from personal_state_engine.zero_cost_baselines import bm25_rank, random_rank, recency_rank, tfidf_rank

HERE = Path(__file__).resolve().parent
CASES_PATH = HERE / "cases.jsonl"
MANIFEST_PATH = HERE / "manifest.json"
CONFIG_PATH = ROOT / "experiments" / "configs" / "candidate-v6-v1.json"
FREEZE_MARKER_PATH = ROOT / "results" / "candidate-v6" / "freeze-marker-v1.json"

EXPECTED_CANDIDATE_SOURCE_SHA256 = "c540056c6f30f0145ab8ef8c10be3abcae2ed24e6a087a2d9a3531bc5e545325"
EXPECTED_CANDIDATE_CONFIG_SHA256 = "067bfa64d97bf2eb1f7208082c36d202118a0e50a2414fc345bf328f83cab5b1"
EXPECTED_DATASET_SHA256 = "855f812b3eec93f3229fe804ebd20e6e86baee5f99e9b322d11c114821215dc7"
BOOTSTRAP_SEED = 20260813
BOOTSTRAP_REPETITIONS = 10000
NONINFERIORITY_MARGIN = 0.03


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in CASES_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def reciprocal_rank(ranking: list[str], relevant: list[str]) -> float:
    relevant_set = set(relevant)
    for index, memory_id in enumerate(ranking, 1):
        if memory_id in relevant_set:
            return 1.0 / index
    return 0.0


def ranking_metrics(cases: list[dict[str, Any]], ranker: Callable[[dict[str, Any], int], list[str]]) -> dict[str, float]:
    answerable = [case for case in cases if case["relevant_memory_ids"]]
    no_evidence = [case for case in cases if not case["relevant_memory_ids"]]
    rankings = {case["id"]: ranker(case, 5) for case in cases}
    rrs = [reciprocal_rank(rankings[case["id"]], case["relevant_memory_ids"]) for case in answerable]

    def recall_at(k: int) -> float:
        hits = sum(bool(set(rankings[c["id"]][:k]) & set(c["relevant_memory_ids"])) for c in answerable)
        return hits / len(answerable)

    answered = sum(bool(rankings[c["id"]]) for c in answerable)
    false_retrievals = sum(bool(rankings[c["id"]]) for c in no_evidence)
    return {
        "MRR": sum(rrs) / len(rrs),
        "R@1": recall_at(1),
        "R@3": recall_at(3),
        "R@5": recall_at(5),
        "answerable_recall": answered / len(answerable),
        "false_abstention": 1.0 - answered / len(answerable),
        "no_evidence_false_retrieval": false_retrievals / len(no_evidence),
        "abstention_accuracy": 1.0 - false_retrievals / len(no_evidence),
    }


def wilson(successes: int, n: int, z: float = 1.959963984540054) -> list[float]:
    if n == 0:
        return [0.0, 0.0]
    p = successes / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return [max(0.0, center - half), min(1.0, center + half)]


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - pos) + ordered[hi] * (pos - lo)


def paired_bootstrap(answerable: list[dict[str, Any]], v2_rankings: dict[str, list[str]], v6_rankings: dict[str, list[str]]) -> dict[str, Any]:
    pairs = [
        (
            reciprocal_rank(v6_rankings[c["id"]], c["relevant_memory_ids"]),
            reciprocal_rank(v2_rankings[c["id"]], c["relevant_memory_ids"]),
        )
        for c in answerable
    ]
    observed = sum(a - b for a, b in pairs) / len(pairs)
    rng = random.Random(BOOTSTRAP_SEED)
    deltas: list[float] = []
    for _ in range(BOOTSTRAP_REPETITIONS):
        sample = [pairs[rng.randrange(len(pairs))] for _ in range(len(pairs))]
        deltas.append(sum(a - b for a, b in sample) / len(sample))
    lower = percentile(deltas, 0.025)
    upper = percentile(deltas, 0.975)
    wins = sum(a > b for a, b in pairs)
    ties = sum(a == b for a, b in pairs)
    losses = sum(a < b for a, b in pairs)
    return {
        "metric": "answerable_case_reciprocal_rank_mrr",
        "candidate_v6_minus_candidate_v2": observed,
        "repetitions": BOOTSTRAP_REPETITIONS,
        "seed": BOOTSTRAP_SEED,
        "ci_95": [lower, upper],
        "noninferiority_margin": NONINFERIORITY_MARGIN,
        "rule": "lower_95_ci_bound_gte_minus_margin",
        "noninferiority_supported": lower >= -NONINFERIORITY_MARGIN - 1e-12,
        "wins_ties_losses": [wins, ties, losses],
        "bootstrap_fraction_delta_gte_minus_margin": sum(delta >= -NONINFERIORITY_MARGIN for delta in deltas) / len(deltas),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE_MARKER_PATH.read_text(encoding="utf-8"))
    cases = load_cases()

    source_sha = sha256_path(ROOT / "src" / "personal_state_engine" / "candidate_v6.py")
    config_sha = sha256_path(CONFIG_PATH)
    dataset_sha = sha256_path(CASES_PATH)
    if freeze["status"] != "FROZEN":
        raise SystemExit("Candidate-v6 is not frozen")
    if source_sha != EXPECTED_CANDIDATE_SOURCE_SHA256:
        raise SystemExit("frozen Candidate-v6 source identity mismatch")
    if config_sha != EXPECTED_CANDIDATE_CONFIG_SHA256:
        raise SystemExit("frozen Candidate-v6 config identity mismatch")
    if dataset_sha != EXPECTED_DATASET_SHA256 or dataset_sha != manifest["expected_dataset_sha256"]:
        raise SystemExit("protected validation dataset identity mismatch")
    if len(cases) != 80 or sum(bool(c["relevant_memory_ids"]) for c in cases) != 40:
        raise SystemExit("protected validation count contract mismatch")

    rankers: dict[str, Callable[[dict[str, Any], int], list[str]]] = {
        "candidate_v2": pse_candidate_v2_rank,
        "candidate_v3": pse_candidate_v3_rank,
        "candidate_v4": pse_candidate_v4_rank,
        "candidate_v5": pse_candidate_v5_rank,
        "candidate_v6": pse_candidate_v6_rank,
        "bm25_local": bm25_rank,
        "tfidf_local": tfidf_rank,
        "deterministic_random": random_rank,
        "recency": recency_rank,
    }
    metrics = {name: ranking_metrics(cases, ranker) for name, ranker in rankers.items()}

    predictions: list[dict[str, Any]] = []
    v2_rankings: dict[str, list[str]] = {}
    v6_rankings: dict[str, list[str]] = {}
    verdict_matches = 0
    for case in cases:
        v2 = pse_candidate_v2_rank(case, 5)
        v6 = pse_candidate_v6_rank(case, 5)
        signature = answerability_signature(case, v2)
        v2_rankings[case["id"]] = v2
        v6_rankings[case["id"]] = v6
        expected = case["expected_candidate_v6_verdict"]
        verdict_matches += int(signature["verdict"] == expected)
        predictions.append({
            "case_id": case["id"],
            "category": case["category"],
            "answerable": bool(case["relevant_memory_ids"]),
            "relevant_memory_ids": case["relevant_memory_ids"],
            "candidate_v2_ranking": v2,
            "candidate_v6_ranking": v6,
            "candidate_v6_verdict": signature["verdict"],
            "expected_candidate_v6_verdict": expected,
            "candidate_v6_verdict_match": signature["verdict"] == expected,
        })

    v2 = metrics["candidate_v2"]
    v6 = metrics["candidate_v6"]
    thresholds = config["selection_thresholds"]
    deficits = {name: v2[name] - v6[name] for name in ("MRR", "R@1", "R@3", "R@5")}
    reduction = v2["no_evidence_false_retrieval"] - v6["no_evidence_false_retrieval"]
    guardrail_checks = {
        "mrr_deficit": deficits["MRR"] <= thresholds["mrr_deficit_max_vs_candidate_v2"] + 1e-12,
        "r1_deficit": deficits["R@1"] <= thresholds["r1_deficit_max_vs_candidate_v2"] + 1e-12,
        "r3_deficit": deficits["R@3"] <= thresholds["r3_deficit_max_vs_candidate_v2"] + 1e-12,
        "r5_deficit": deficits["R@5"] <= thresholds["r5_deficit_max_vs_candidate_v2"] + 1e-12,
        "answerable_recall": v6["answerable_recall"] >= thresholds["answerable_recall_min"] - 1e-12,
        "false_abstention": v6["false_abstention"] <= thresholds["false_abstention_max"] + 1e-12,
        "abstention_accuracy": v6["abstention_accuracy"] >= thresholds["abstention_accuracy_min"] - 1e-12,
        "no_evidence_false_retrieval": v6["no_evidence_false_retrieval"] <= thresholds["no_evidence_false_retrieval_max"] + 1e-12,
        "false_retrieval_reduction": reduction >= thresholds["no_evidence_false_retrieval_absolute_reduction_vs_candidate_v2_min"] - 1e-12,
    }

    answerable = [case for case in cases if case["relevant_memory_ids"]]
    no_evidence = [case for case in cases if not case["relevant_memory_ids"]]
    stats = paired_bootstrap(answerable, v2_rankings, v6_rankings)
    answered = sum(bool(v6_rankings[c["id"]]) for c in answerable)
    false_retrievals = sum(bool(v6_rankings[c["id"]]) for c in no_evidence)
    intervals = {
        "answerable_recall": {"successes": answered, "n": len(answerable), "wilson_95": wilson(answered, len(answerable))},
        "false_abstention": {"successes": len(answerable) - answered, "n": len(answerable), "wilson_95": wilson(len(answerable) - answered, len(answerable))},
        "abstention_accuracy": {"successes": len(no_evidence) - false_retrievals, "n": len(no_evidence), "wilson_95": wilson(len(no_evidence) - false_retrievals, len(no_evidence))},
        "no_evidence_false_retrieval": {"successes": false_retrievals, "n": len(no_evidence), "wilson_95": wilson(false_retrievals, len(no_evidence))},
    }

    protected_pass = all(guardrail_checks.values()) and stats["noninferiority_supported"]
    summary = {
        "schema_version": "candidate-v6-protected-validation-summary-v1",
        "candidate": "candidate-v6",
        "candidate_status": "PROTECTED_VALIDATION_PASS" if protected_pass else "REJECTED_BY_FROZEN_PROTECTED_VALIDATION_GUARDRAILS",
        "dataset": {
            "benchmark_id": manifest["benchmark_id"],
            "case_count": len(cases),
            "answerable_count": len(answerable),
            "no_evidence_count": len(no_evidence),
            "sha256": dataset_sha,
        },
        "frozen_candidate": {
            "source_sha256": source_sha,
            "config_sha256": config_sha,
            "freeze_marker_commit": manifest["candidate_freeze_marker_commit"],
            "changed_after_freeze": False,
        },
        "metrics": metrics,
        "candidate_v6_verdict_accuracy": verdict_matches / len(cases),
        "retrieval_deficits_vs_candidate_v2": deficits,
        "no_evidence_false_retrieval_absolute_reduction_vs_candidate_v2": reduction,
        "guardrails": {"checks": guardrail_checks, "all_pass": all(guardrail_checks.values())},
        "statistics": stats,
        "wilson_intervals": intervals,
        "protected_validation_pass": protected_pass,
        "formal_execution": {"allowed_count": 1, "this_execution": 1, "rerun_authorized": False},
        "integrity": {
            "post_result_candidate_tuning_allowed": False,
            "post_result_dataset_editing_allowed": False,
            "candidate_v5_modified": False,
            "sealed_final_accessed": False,
            "monetary_cost_usd": 0,
            "paid_api": False,
            "paid_gpu": False,
            "paid_inference": False,
        },
    }

    (args.output_dir / "predictions-v1.json").write_text(json.dumps(predictions, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "validation-summary-v1.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "validation-statistics-v1.json").write_text(json.dumps({"paired_bootstrap": stats, "wilson_intervals": intervals}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if protected_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
