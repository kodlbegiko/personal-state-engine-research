from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v3 import pse_candidate_v3_rank
from personal_state_engine.candidate_v4 import pse_candidate_v4_rank
from personal_state_engine.candidate_v5 import pse_candidate_v5_rank
from personal_state_engine.candidate_v6 import answerability_signature, parse_evidence_object, pse_candidate_v6_rank
from personal_state_engine.zero_cost_baselines import bm25_rank, evaluate_cases, random_rank, recency_rank, tfidf_rank

DEV_ROOT = ROOT / "benchmarks" / "algorithm-development" / "candidate-v6-development-v1"
DEV_GENERATOR = DEV_ROOT / "generate.py"
DEV_MANIFEST = DEV_ROOT / "manifest.json"
DEV_CASES = DEV_ROOT / "cases.jsonl"
CONFIG_PATH = ROOT / "experiments" / "configs" / "candidate-v6-v1.json"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical_jsonl(cases: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n" for case in cases)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _answerability_metrics(cases: list[dict[str, Any]], ranker: Callable[[dict[str, Any], int], list[str]]) -> dict[str, Any]:
    answerable = [case for case in cases if case["relevant_memory_ids"]]
    no_evidence = [case for case in cases if not case["relevant_memory_ids"]]
    answerable_answered = sum(bool(ranker(case, 5)) for case in answerable)
    no_evidence_retrieved = sum(bool(ranker(case, 5)) for case in no_evidence)
    answerable_recall = answerable_answered / len(answerable)
    false_retrieval = no_evidence_retrieved / len(no_evidence)
    return {
        "answerable_recall": answerable_recall,
        "false_abstention": 1.0 - answerable_recall,
        "no_evidence_false_retrieval": false_retrieval,
        "abstention_accuracy": 1.0 - false_retrieval,
    }


def _metrics(cases: list[dict[str, Any]], ranker: Callable[[dict[str, Any], int], list[str]]) -> dict[str, Any]:
    base = evaluate_cases(cases, ranker, 5)["metrics"]
    return {
        "MRR": base["MRR"],
        "R@1": base["recall@1"],
        "R@3": base["recall@3"],
        "R@5": base["recall@5"],
        **_answerability_metrics(cases, ranker),
    }


def _diagnostic_accuracy(cases: list[dict[str, Any]]) -> dict[str, Any]:
    family_totals: dict[str, int] = {}
    family_correct: dict[str, int] = {}
    assertion_total = assertion_correct = 0
    meta_total = meta_correct = 0
    no_value_total = no_value_correct = 0

    for case in cases:
        by_id = {memory["id"]: memory for memory in case["memories"]}
        for target in case.get("diagnostic_targets", []):
            family = target["diagnostic_family"]
            expected = target["expected_assertion_type"]
            obj = parse_evidence_object(by_id[target["memory_id"]], case["query"])
            correct = obj.assertion_type == expected
            family_totals[family] = family_totals.get(family, 0) + 1
            family_correct[family] = family_correct.get(family, 0) + int(correct)
            if family == "assertion_extraction":
                assertion_total += 1
                assertion_correct += int(correct)
            if family == "meta_discourse":
                meta_total += 1
                meta_correct += int(correct and obj.object_or_value is None)
            if family == "explicit_no_value":
                no_value_total += 1
                no_value_correct += int(correct and obj.object_or_value is None)

    contradiction_cases = [case for case in cases if case["category"] == "contradiction"]
    contradiction_correct = sum(answerability_signature(case)["verdict"] == "CONTRADICTED" for case in contradiction_cases)
    temporal_cases = [case for case in cases if case["category"] == "stale_only"]
    temporal_correct = sum(answerability_signature(case)["verdict"] == "INSUFFICIENT" for case in temporal_cases)

    def ratio(correct: int, total: int) -> float:
        return correct / total if total else 1.0

    return {
        "assertion_extraction_accuracy": ratio(assertion_correct, assertion_total),
        "meta_discourse_rejection_accuracy": ratio(meta_correct, meta_total),
        "explicit_no_value_detection_accuracy": ratio(no_value_correct, no_value_total),
        "contradiction_detection_accuracy": ratio(contradiction_correct, len(contradiction_cases)),
        "temporal_resolution_accuracy": ratio(temporal_correct, len(temporal_cases)),
        "family_counts": {
            family: {"correct": family_correct.get(family, 0), "total": total, "accuracy": ratio(family_correct.get(family, 0), total)}
            for family, total in sorted(family_totals.items())
        },
    }


def _guardrails(metrics: dict[str, dict[str, Any]], diagnostics: dict[str, Any], thresholds: dict[str, float]) -> dict[str, Any]:
    v2 = metrics["candidate_v2"]
    v6 = metrics["candidate_v6"]
    deficits = {
        "MRR": v2["MRR"] - v6["MRR"],
        "R@1": v2["R@1"] - v6["R@1"],
        "R@3": v2["R@3"] - v6["R@3"],
        "R@5": v2["R@5"] - v6["R@5"],
    }
    reduction = v2["no_evidence_false_retrieval"] - v6["no_evidence_false_retrieval"]
    checks = {
        "mrr_deficit": deficits["MRR"] <= thresholds["mrr_deficit_max_vs_candidate_v2"] + 1e-12,
        "r1_deficit": deficits["R@1"] <= thresholds["r1_deficit_max_vs_candidate_v2"] + 1e-12,
        "r3_deficit": deficits["R@3"] <= thresholds["r3_deficit_max_vs_candidate_v2"] + 1e-12,
        "r5_deficit": deficits["R@5"] <= thresholds["r5_deficit_max_vs_candidate_v2"] + 1e-12,
        "answerable_recall": v6["answerable_recall"] >= thresholds["answerable_recall_min"] - 1e-12,
        "false_abstention": v6["false_abstention"] <= thresholds["false_abstention_max"] + 1e-12,
        "abstention_accuracy": v6["abstention_accuracy"] >= thresholds["abstention_accuracy_min"] - 1e-12,
        "no_evidence_false_retrieval": v6["no_evidence_false_retrieval"] <= thresholds["no_evidence_false_retrieval_max"] + 1e-12,
        "false_retrieval_reduction": reduction >= thresholds["no_evidence_false_retrieval_absolute_reduction_vs_candidate_v2_min"] - 1e-12,
        "assertion_extraction_accuracy": diagnostics["assertion_extraction_accuracy"] >= thresholds["assertion_extraction_accuracy_min"] - 1e-12,
        "meta_discourse_rejection_accuracy": diagnostics["meta_discourse_rejection_accuracy"] >= thresholds["meta_discourse_rejection_accuracy_min"] - 1e-12,
        "explicit_no_value_detection_accuracy": diagnostics["explicit_no_value_detection_accuracy"] >= thresholds["explicit_no_value_detection_accuracy_min"] - 1e-12,
        "contradiction_detection_accuracy": diagnostics["contradiction_detection_accuracy"] >= thresholds["contradiction_detection_accuracy_min"] - 1e-12,
        "temporal_resolution_accuracy": diagnostics["temporal_resolution_accuracy"] >= thresholds["temporal_resolution_accuracy_min"] - 1e-12,
    }
    return {
        "development_only": True,
        "retrieval_deficits_vs_candidate_v2": deficits,
        "no_evidence_false_retrieval_absolute_reduction_vs_candidate_v2": reduction,
        "checks": checks,
        "pass": all(checks.values()),
        "selection_authorized": False,
        "note": "Development guardrails authorize Candidate-v6 freeze only; they are not protected validation or Gate E selection evidence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "candidate-v6" / "development-summary-v1.json")
    parser.add_argument("--materialize-cases", type=Path, default=None)
    args = parser.parse_args()

    generator = _load_module(DEV_GENERATOR, "candidate_v6_development_generator")
    cases = generator.build_cases()
    canonical = _canonical_jsonl(cases)
    dataset_sha = _sha256_text(canonical)
    manifest = json.loads(DEV_MANIFEST.read_text(encoding="utf-8"))
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    if dataset_sha != manifest["expected_dataset_sha256"]:
        raise SystemExit(f"dataset SHA mismatch: {dataset_sha} != {manifest['expected_dataset_sha256']}")
    if len(cases) != manifest["case_count"]:
        raise SystemExit(f"case count mismatch: {len(cases)} != {manifest['case_count']}")
    if DEV_CASES.exists():
        committed = DEV_CASES.read_text(encoding="utf-8")
        if committed != canonical:
            raise SystemExit("committed cases.jsonl differs from deterministic generator output")
    else:
        raise SystemExit("committed cases.jsonl is missing")

    if args.materialize_cases is not None:
        args.materialize_cases.parent.mkdir(parents=True, exist_ok=True)
        args.materialize_cases.write_text(canonical, encoding="utf-8")

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
    metrics = {name: _metrics(cases, ranker) for name, ranker in rankers.items()}
    diagnostics = _diagnostic_accuracy(cases)
    guardrails = _guardrails(metrics, diagnostics, config["selection_thresholds"])
    result = {
        "schema_version": "candidate-v6-development-summary-v1",
        "phase": "DEVELOPMENT_DIAGNOSTIC_ONLY",
        "dataset": {
            "case_count": len(cases),
            "answerable_count": sum(bool(case["relevant_memory_ids"]) for case in cases),
            "no_evidence_count": sum(not bool(case["relevant_memory_ids"]) for case in cases),
            "sha256": dataset_sha,
            "seed": manifest["seed"],
        },
        "metrics": metrics,
        "diagnostics": diagnostics,
        "candidate_v6_development_guardrails": guardrails,
        "integrity": {
            "candidate_v5_modified": False,
            "candidate_v5_protected_validation_used_as_fresh_confirmatory": False,
            "sealed_final_accessed": False,
            "monetary_cost_usd": 0,
            "paid_api": False,
            "paid_gpu": False,
            "paid_inference": False,
        },
        "formal_gate_effect": "NONE_UNTIL_POST_FREEZE_PROTECTED_EVIDENCE",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if guardrails["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
