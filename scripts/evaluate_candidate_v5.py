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
from personal_state_engine.zero_cost_baselines import (
    bm25_rank,
    evaluate_cases,
    pse_current_rank,
    random_rank,
    recency_rank,
    tfidf_rank,
)

DEV_GENERATOR = ROOT / "benchmarks" / "algorithm-development" / "candidate-v5-dev-v1" / "generator.py"
DEV_MANIFEST = ROOT / "benchmarks" / "algorithm-development" / "candidate-v5-dev-v1" / "manifest.json"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import generator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical_jsonl(cases: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(case, ensure_ascii=False, sort_keys=True) for case in cases) + "\n"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _answerability_metrics(cases: list[dict[str, Any]], ranker: Callable[[dict[str, Any], int], list[str]]) -> dict[str, Any]:
    answerable = [case for case in cases if case["relevant_memory_ids"]]
    no_evidence = [case for case in cases if not case["relevant_memory_ids"]]

    answerable_answered = sum(bool(ranker(case, 5)) for case in answerable)
    no_evidence_retrieved = sum(bool(ranker(case, 5)) for case in no_evidence)

    answerable_recall = answerable_answered / len(answerable) if answerable else None
    false_abstention = 1.0 - answerable_recall if answerable_recall is not None else None
    false_retrieval = no_evidence_retrieved / len(no_evidence) if no_evidence else None
    abstention_accuracy = 1.0 - false_retrieval if false_retrieval is not None else None
    return {
        "answerable_recall": answerable_recall,
        "false_abstention": false_abstention,
        "no_evidence_false_retrieval": false_retrieval,
        "abstention_accuracy": abstention_accuracy,
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


def _guardrails(metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    v2 = metrics["candidate_v2"]
    v5 = metrics["candidate_v5"]
    deficits = {
        "MRR": v2["MRR"] - v5["MRR"],
        "R@1": v2["R@1"] - v5["R@1"],
        "R@3": v2["R@3"] - v5["R@3"],
        "R@5": v2["R@5"] - v5["R@5"],
    }
    false_retrieval_reduction = v2["no_evidence_false_retrieval"] - v5["no_evidence_false_retrieval"]
    checks = {
        "mrr_deficit_le_0_03": deficits["MRR"] <= 0.03 + 1e-12,
        "r1_deficit_le_0_03": deficits["R@1"] <= 0.03 + 1e-12,
        "r3_deficit_le_0_02": deficits["R@3"] <= 0.02 + 1e-12,
        "r5_deficit_le_0_02": deficits["R@5"] <= 0.02 + 1e-12,
        "answerable_recall_ge_0_90": v5["answerable_recall"] >= 0.90,
        "false_abstention_le_0_10": v5["false_abstention"] <= 0.10,
        "abstention_accuracy_ge_0_80": v5["abstention_accuracy"] >= 0.80,
        "false_retrieval_le_0_20": v5["no_evidence_false_retrieval"] <= 0.20,
        "false_retrieval_absolute_reduction_ge_0_50": false_retrieval_reduction >= 0.50,
    }
    return {
        "development_only": True,
        "retrieval_deficits_vs_candidate_v2": deficits,
        "no_evidence_false_retrieval_absolute_reduction_vs_candidate_v2": false_retrieval_reduction,
        "checks": checks,
        "pass": all(checks.values()),
        "selection_authorized": False,
        "note": "Development guardrails justify freezing only; they are not protected validation or Gate E selection evidence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "candidate-v5" / "development-summary-v1.json")
    parser.add_argument("--materialize-cases", type=Path, default=None)
    args = parser.parse_args()

    generator = _load_module(DEV_GENERATOR, "candidate_v5_dev_generator")
    cases = generator.build_cases()
    canonical = _canonical_jsonl(cases)
    dataset_sha = _sha256_text(canonical)
    manifest = json.loads(DEV_MANIFEST.read_text(encoding="utf-8"))
    expected_sha = manifest["expected_dataset_sha256"]
    if dataset_sha != expected_sha:
        raise SystemExit(f"dataset SHA mismatch: {dataset_sha} != {expected_sha}")
    if len(cases) != manifest["case_count"]:
        raise SystemExit(f"case count mismatch: {len(cases)} != {manifest['case_count']}")

    if args.materialize_cases is not None:
        args.materialize_cases.parent.mkdir(parents=True, exist_ok=True)
        args.materialize_cases.write_text(canonical, encoding="utf-8")

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
    metrics = {name: _metrics(cases, ranker) for name, ranker in rankers.items()}
    result = {
        "schema_version": "candidate-v5-development-summary-v1",
        "phase": "DEVELOPMENT_DIAGNOSTIC_ONLY",
        "dataset": {
            "case_count": len(cases),
            "answerable_count": sum(bool(case["relevant_memory_ids"]) for case in cases),
            "no_evidence_count": sum(not bool(case["relevant_memory_ids"]) for case in cases),
            "sha256": dataset_sha,
            "seed": manifest["seed"],
        },
        "metrics": metrics,
        "candidate_v5_development_guardrails": _guardrails(metrics),
        "integrity": {
            "v6_used_as_confirmatory": False,
            "sealed_final_accessed": False,
            "candidate_v4_modified": False,
            "monetary_cost_usd": 0,
            "paid_api": False,
            "paid_gpu": False,
        },
        "formal_gate_effect": "NONE_UNTIL_POST_FREEZE_PROTECTED_EVIDENCE",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["candidate_v5_development_guardrails"]["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
