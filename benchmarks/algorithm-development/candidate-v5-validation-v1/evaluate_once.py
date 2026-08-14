from __future__ import annotations

import argparse
import hashlib
import json
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
from personal_state_engine.zero_cost_baselines import (
    bm25_rank,
    evaluate_cases,
    pse_current_rank,
    random_rank,
    recency_rank,
    tfidf_rank,
)

HERE = Path(__file__).resolve().parent
CASES = HERE / "cases.jsonl"
MANIFEST = HERE / "manifest.json"
CONFIG = ROOT / "experiments" / "configs" / "candidate-v5-v1.json"
FREEZE = ROOT / "results" / "candidate-v5" / "candidate-v5-freeze-manifest-v1.json"
EXPECTED_DATASET_SHA256 = "9fe8b06b6a1ee051476171328e0cd330978fe996cdba8b6cfbf932cd23334af5"
EXPECTED_SOURCE_SHA256 = "f85be743db4d2658c90c5d2b8ec8dee0f0e1f4bdfe3e92066cbd2818c749d975"
EXPECTED_CONFIG_SHA256 = "b0106d0560fae1e2a08a3107dda135d6f015ca3260a41d4daeed179da8e04e6a"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cases() -> list[dict[str, Any]]:
    raw = CASES.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_DATASET_SHA256:
        raise SystemExit(f"protected validation dataset hash mismatch: {digest}")
    cases = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    if len(cases) != 48:
        raise SystemExit(f"protected validation case count mismatch: {len(cases)}")
    if sum(bool(c["relevant_memory_ids"]) for c in cases) != 24:
        raise SystemExit("protected validation answerable count mismatch")
    if sum(not bool(c["relevant_memory_ids"]) for c in cases) != 24:
        raise SystemExit("protected validation no-evidence count mismatch")
    return cases


def verify_frozen_candidate() -> dict[str, Any]:
    source = ROOT / "src" / "personal_state_engine" / "candidate_v5.py"
    source_sha = sha256(source)
    config_sha = sha256(CONFIG)
    if source_sha != EXPECTED_SOURCE_SHA256:
        raise SystemExit(f"Candidate-v5 source changed after freeze: {source_sha}")
    if config_sha != EXPECTED_CONFIG_SHA256:
        raise SystemExit(f"Candidate-v5 config changed after freeze: {config_sha}")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    if freeze.get("status") != "FROZEN":
        raise SystemExit("Candidate-v5 freeze manifest is not FROZEN")
    if freeze["source"]["sha256"] != source_sha or freeze["config"]["sha256"] != config_sha:
        raise SystemExit("Candidate-v5 freeze manifest identity mismatch")
    return {
        "source_sha256": source_sha,
        "config_sha256": config_sha,
        "freeze_commit": freeze["freeze_commit"],
        "changed_after_freeze": False,
    }


def answerability_metrics(cases: list[dict[str, Any]], ranker: Callable[[dict[str, Any], int], list[str]]) -> dict[str, float]:
    answerable = [case for case in cases if case["relevant_memory_ids"]]
    no_evidence = [case for case in cases if not case["relevant_memory_ids"]]
    answered = sum(bool(ranker(case, 5)) for case in answerable)
    false_retrieved = sum(bool(ranker(case, 5)) for case in no_evidence)
    answerable_recall = answered / len(answerable)
    false_retrieval = false_retrieved / len(no_evidence)
    return {
        "answerable_recall": answerable_recall,
        "false_abstention": 1.0 - answerable_recall,
        "no_evidence_false_retrieval": false_retrieval,
        "abstention_accuracy": 1.0 - false_retrieval,
    }


def metrics(cases: list[dict[str, Any]], ranker: Callable[[dict[str, Any], int], list[str]]) -> dict[str, float]:
    base = evaluate_cases(cases, ranker, 5)["metrics"]
    return {
        "MRR": base["MRR"],
        "R@1": base["recall@1"],
        "R@3": base["recall@3"],
        "R@5": base["recall@5"],
        **answerability_metrics(cases, ranker),
    }


def case_records(cases: list[dict[str, Any]], rankers: dict[str, Callable[[dict[str, Any], int], list[str]]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for case in cases:
        record = {
            "id": case["id"],
            "category": case["category"],
            "answerable": bool(case["relevant_memory_ids"]),
            "relevant_memory_ids": case["relevant_memory_ids"],
            "rankings": {},
        }
        for name, ranker in rankers.items():
            record["rankings"][name] = ranker(case, 5)
        out.append(record)
    return out


def guardrails(all_metrics: dict[str, dict[str, float]], frozen_config: dict[str, Any]) -> dict[str, Any]:
    thresholds = frozen_config["selection_thresholds"]
    v2 = all_metrics["candidate_v2"]
    v5 = all_metrics["candidate_v5"]
    deficits = {
        "MRR": v2["MRR"] - v5["MRR"],
        "R@1": v2["R@1"] - v5["R@1"],
        "R@3": v2["R@3"] - v5["R@3"],
        "R@5": v2["R@5"] - v5["R@5"],
    }
    improvement = v2["no_evidence_false_retrieval"] - v5["no_evidence_false_retrieval"]
    checks = {
        "mrr_deficit": deficits["MRR"] <= thresholds["mrr_deficit_max_vs_candidate_v2"] + 1e-12,
        "r1_deficit": deficits["R@1"] <= thresholds["r1_deficit_max_vs_candidate_v2"] + 1e-12,
        "r3_deficit": deficits["R@3"] <= thresholds["r3_deficit_max_vs_candidate_v2"] + 1e-12,
        "r5_deficit": deficits["R@5"] <= thresholds["r5_deficit_max_vs_candidate_v2"] + 1e-12,
        "answerable_recall": v5["answerable_recall"] >= thresholds["answerable_recall_min"] - 1e-12,
        "false_abstention": v5["false_abstention"] <= thresholds["false_abstention_max"] + 1e-12,
        "abstention_accuracy": v5["abstention_accuracy"] >= thresholds["abstention_accuracy_min"] - 1e-12,
        "no_evidence_false_retrieval": v5["no_evidence_false_retrieval"] <= thresholds["no_evidence_false_retrieval_max"] + 1e-12,
        "absolute_false_retrieval_reduction": improvement >= thresholds["no_evidence_false_retrieval_absolute_reduction_vs_candidate_v2_min"] - 1e-12,
    }
    return {
        "threshold_source": "experiments/configs/candidate-v5-v1.json",
        "thresholds": thresholds,
        "retrieval_deficits_vs_candidate_v2": deficits,
        "no_evidence_false_retrieval_absolute_reduction_vs_candidate_v2": improvement,
        "checks": checks,
        "pass": all(checks.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["dataset_sha256"] != EXPECTED_DATASET_SHA256:
        raise SystemExit("validation manifest dataset hash mismatch")
    if not manifest["created_after_candidate_v5_freeze"] or not manifest["one_formal_execution_only"]:
        raise SystemExit("validation manifest integrity flags invalid")

    frozen_identity = verify_frozen_candidate()
    cases = load_cases()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    rankers: dict[str, Callable[[dict[str, Any], int], list[str]]] = {
        "candidate_v2": pse_candidate_v2_rank,
        "candidate_v3": pse_candidate_v3_rank,
        "candidate_v4": pse_candidate_v4_rank,
        "candidate_v5": pse_candidate_v5_rank,
        "current_baseline": pse_current_rank,
        "bm25_local": bm25_rank,
        "tfidf_local": tfidf_rank,
        "deterministic_random": random_rank,
        "recency": recency_rank,
    }
    all_metrics = {name: metrics(cases, ranker) for name, ranker in rankers.items()}
    frozen_guardrails = guardrails(all_metrics, config)
    records = case_records(cases, rankers)

    result = {
        "schema_version": "candidate-v5-protected-validation-summary-v1",
        "phase": "PROTECTED_VALIDATION_SINGLE_FORMAL_EXECUTION",
        "dataset": {
            "path": str(CASES.relative_to(ROOT)),
            "sha256": EXPECTED_DATASET_SHA256,
            "case_count": 48,
            "answerable_count": 24,
            "no_evidence_count": 24,
        },
        "candidate_v5_frozen_identity": frozen_identity,
        "metrics": all_metrics,
        "candidate_v5_guardrails": frozen_guardrails,
        "case_records": records,
        "verdict": "VALIDATION_PASS" if frozen_guardrails["pass"] else "VALIDATION_FAIL_CANDIDATE_V5_REMAINS_FROZEN",
        "post_result_patch_authorized": False,
        "integrity": {
            "candidate_v5_modified_after_freeze": False,
            "v6_used_as_validation": False,
            "sealed_final_accessed": False,
            "negative_evidence_deleted": False,
            "monetary_cost_usd": 0,
            "paid_api": False,
            "paid_gpu": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": result["verdict"],
        "dataset_sha256": EXPECTED_DATASET_SHA256,
        "candidate_v5_metrics": all_metrics["candidate_v5"],
        "candidate_v2_metrics": all_metrics["candidate_v2"],
        "guardrails": frozen_guardrails,
    }, indent=2, sort_keys=True))
    return 0 if frozen_guardrails["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
