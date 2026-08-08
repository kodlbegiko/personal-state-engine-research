#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

EXPECTED_CORPUS_SHA256 = "02e3afef1e17d9d8991ea7172cbfc19ad239874c914a088c20e5de6a146f7a1d"
EXPECTED_CANDIDATE_V2_FREEZE = "d627f61d0888306a97f3ef0b78aa29dc00c444bb"
EXPECTED_CANDIDATE_V2_SOURCE = "52c8341e4317a1492ec5511907414c7deee77ef6"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize(result: dict[str, Any]) -> dict[str, Any]:
    metrics = result["metrics"]
    return {
        "case_count": result["case_count"],
        "answerable_case_count": result["answerable_case_count"],
        "abstention_case_count": result["abstention_case_count"],
        "mrr": metrics.get("MRR"),
        "recall_at_1": metrics.get("recall@1"),
        "recall_at_3": metrics.get("recall@3"),
        "recall_at_5": metrics.get("recall@5"),
        "precision_at_1": metrics.get("precision@1"),
        "precision_at_3": metrics.get("precision@3"),
        "precision_at_5": metrics.get("precision@5"),
        "ndcg_at_5": metrics.get("ndcg@5"),
        "irrelevant_retrieval_rate": metrics.get("irrelevant_retrieval_rate"),
        "abstention_accuracy": metrics.get("abstention_accuracy"),
        "false_retrieval_rate": (1.0 - metrics["abstention_accuracy"]) if metrics.get("abstention_accuracy") is not None else None,
    }


def rr(case: dict[str, Any], ranker: Callable[[dict[str, Any], int], list[str]]) -> float:
    relevant = set(case["relevant_memory_ids"])
    if not relevant:
        return 0.0
    return next((1.0 / (index + 1) for index, memory_id in enumerate(ranker(case, 5)) if memory_id in relevant), 0.0)


def win_tie_loss(cases: list[dict[str, Any]], left: Callable[[dict[str, Any], int], list[str]], right: Callable[[dict[str, Any], int], list[str]]) -> dict[str, int]:
    wins = ties = losses = 0
    for case in cases:
        if not case["relevant_memory_ids"]:
            continue
        delta = rr(case, right) - rr(case, left)
        if delta > 0:
            wins += 1
        elif delta < 0:
            losses += 1
        else:
            ties += 1
    return {"right_wins": wins, "ties": ties, "right_losses": losses}


def main() -> int:
    from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
    from personal_state_engine.zero_cost_baselines import (
        RANKERS,
        bootstrap_mrr_delta,
        evaluate_cases,
        pse_candidate_v1_rank,
        pse_current_rank,
    )

    parser = argparse.ArgumentParser(description="Evaluate frozen post-candidate adversarial-v4 discrimination benchmark.")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    if sha256_file(args.corpus) != EXPECTED_CORPUS_SHA256:
        raise SystemExit("adversarial-v4 corpus SHA mismatch")
    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if manifest.get("status") != "FROZEN_BEFORE_ANY_V4_SYSTEM_EVALUATION":
        raise SystemExit("v4 manifest is not a pre-evaluation freeze")
    if manifest.get("corpus_sha256") != EXPECTED_CORPUS_SHA256 or manifest.get("case_count") != 24:
        raise SystemExit("v4 manifest corpus mismatch")
    if manifest.get("candidate_v2_freeze_commit") != EXPECTED_CANDIDATE_V2_FREEZE or manifest.get("candidate_v2_source_commit") != EXPECTED_CANDIDATE_V2_SOURCE:
        raise SystemExit("candidate freeze identity mismatch")
    if manifest.get("candidate_source_changed_for_v4") is not False or manifest.get("sealed_final_accessed") is not False:
        raise SystemExit("candidate/integrity freeze violated")
    if protocol.get("status") != "FROZEN_BEFORE_V4_SYSTEM_RESULTS":
        raise SystemExit("v4 evaluation protocol is not frozen pre-result")
    if protocol["benchmark"]["sha256"] != EXPECTED_CORPUS_SHA256:
        raise SystemExit("v4 protocol corpus mismatch")
    if protocol["candidate_lock"]["candidate_v2_freeze_commit"] != EXPECTED_CANDIDATE_V2_FREEZE:
        raise SystemExit("v4 protocol candidate lock mismatch")
    if protocol["integrity"]["sealed_final_accessed"] is not False or float(protocol["integrity"]["new_monetary_cost_usd"]) != 0.0:
        raise SystemExit("v4 protocol integrity/cost boundary invalid")

    cases = list(corpus.get("cases", []))
    if len(cases) != 24 or len({case["id"] for case in cases}) != 24:
        raise SystemExit("v4 corpus must contain exactly 24 unique cases")

    systems: dict[str, Callable[[dict[str, Any], int], list[str]]] = {
        "random": RANKERS["random"],
        "recency": RANKERS["recency"],
        "lexical": RANKERS["lexical"],
        "tfidf_local": RANKERS["tfidf_local"],
        "bm25_local": RANKERS["bm25_local"],
        "hybrid": RANKERS["hybrid"],
        "pse_current_reconstruction": pse_current_rank,
        "pse_candidate_v1": pse_candidate_v1_rank,
        "pse_candidate_v2": pse_candidate_v2_rank,
    }
    if list(systems) != protocol["systems"]:
        raise SystemExit("system evaluation order/scope differs from frozen protocol")

    results = {name: normalize(evaluate_cases(cases, ranker)) for name, ranker in systems.items()}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        grouped[case["category"]].append(case)
    category_results = {
        category: {name: normalize(evaluate_cases(group_cases, ranker)) for name, ranker in systems.items()}
        for category, group_cases in sorted(grouped.items())
    }

    paired = {
        "candidate_v1_vs_current": {
            **bootstrap_mrr_delta(cases, pse_current_rank, pse_candidate_v1_rank),
            "win_tie_loss": win_tie_loss(cases, pse_current_rank, pse_candidate_v1_rank),
            "right_system": "pse_candidate_v1",
        },
        "candidate_v2_vs_current": {
            **bootstrap_mrr_delta(cases, pse_current_rank, pse_candidate_v2_rank),
            "win_tie_loss": win_tie_loss(cases, pse_current_rank, pse_candidate_v2_rank),
            "right_system": "pse_candidate_v2",
        },
        "candidate_v2_vs_candidate_v1": {
            **bootstrap_mrr_delta(cases, pse_candidate_v1_rank, pse_candidate_v2_rank),
            "win_tie_loss": win_tie_loss(cases, pse_candidate_v1_rank, pse_candidate_v2_rank),
            "right_system": "pse_candidate_v2",
        },
    }

    pse_names = ["pse_current_reconstruction", "pse_candidate_v1", "pse_candidate_v2"]
    best_mrr_name = max(pse_names, key=lambda name: float(results[name]["mrr"] or 0.0))
    best_r1_name = max(pse_names, key=lambda name: float(results[name]["recall_at_1"] or 0.0))
    best_mrr = float(results[best_mrr_name]["mrr"] or 0.0)
    best_r1 = float(results[best_r1_name]["recall_at_1"] or 0.0)
    min_mrr_gap = float(protocol["discrimination_rule"]["minimum_mrr_gap_for_sufficient_discrimination"])
    min_r1_gap = float(protocol["discrimination_rule"]["minimum_recall_at_1_gap_for_sufficient_discrimination"])
    baseline_gaps = {}
    sufficient = True
    for baseline in protocol["discrimination_rule"]["baselines_checked"]:
        mrr_gap = best_mrr - float(results[baseline]["mrr"] or 0.0)
        r1_gap = best_r1 - float(results[baseline]["recall_at_1"] or 0.0)
        passes = mrr_gap >= min_mrr_gap and r1_gap >= min_r1_gap
        baseline_gaps[baseline] = {
            "mrr_gap_to_best_pse": mrr_gap,
            "recall_at_1_gap_to_best_pse": r1_gap,
            "passes_preregistered_gap_rule": passes,
        }
        sufficient = sufficient and passes

    discrimination = {
        "status": "SUFFICIENT_FOR_EXACT_A_MEM_FOLLOWUP" if sufficient else "DISCRIMINATION_INSUFFICIENT",
        "best_pse_mrr_system": best_mrr_name,
        "best_pse_mrr": best_mrr,
        "best_pse_recall_at_1_system": best_r1_name,
        "best_pse_recall_at_1": best_r1,
        "minimum_required_mrr_gap": min_mrr_gap,
        "minimum_required_recall_at_1_gap": min_r1_gap,
        "baseline_gaps": baseline_gaps,
        "next_action": protocol["a_mem_next_step_rule"]["if_discrimination_sufficient"] if sufficient else protocol["a_mem_next_step_rule"]["if_discrimination_insufficient"],
    }

    output = {
        "schema_version": "adversarial-v4-discrimination-results-v1",
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "manifest_sha256": sha256_file(args.manifest),
        "protocol_sha256": sha256_file(args.protocol),
        "case_count": 24,
        "answerable_case_count": 22,
        "abstention_case_count": 2,
        "systems": results,
        "by_category": category_results,
        "paired_statistics": paired,
        "discrimination": discrimination,
        "statistical_interpretation": "UNDERPOWERED for pairwise formal claims because n=22 answerable; bootstrap intervals are descriptive.",
        "candidate_v2_changed_for_v4": False,
        "independent_reproduction": False,
        "operator_designed": True,
        "algorithm_parity": "NO",
        "sealed_final_accessed": False,
        "new_monetary_cost_usd": 0.0,
        "claim_boundary": protocol["claim_boundary"],
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    result_path = args.output_root / "results.json"
    write_json(result_path, output)
    registry = {
        "schema_version": "adversarial-v4-artifact-registry-v1",
        "artifact_count": 1,
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "manifest_sha256": sha256_file(args.manifest),
        "protocol_sha256": sha256_file(args.protocol),
        "candidate_v2_freeze_commit": EXPECTED_CANDIDATE_V2_FREEZE,
        "sealed_final_accessed": False,
        "new_monetary_cost_usd": 0.0,
        "artifacts": [{
            "path": result_path.as_posix(),
            "bytes": result_path.stat().st_size,
            "sha256": sha256_file(result_path),
            "generation_command": "python scripts/evaluate_adversarial_v4.py ...",
        }],
    }
    write_json(args.output_root / "artifact-registry.json", registry)
    print(json.dumps({"status": "ADVERSARIAL_V4_EVALUATED", "discrimination": discrimination["status"], "best_mrr": best_mrr, "best_r1": best_r1}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
