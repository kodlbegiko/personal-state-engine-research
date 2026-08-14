#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.zero_cost_baselines import (
    bm25_rank,
    bootstrap_mrr_delta,
    evaluate_cases,
    pse_candidate_v1_rank,
    pse_current_rank,
    random_rank,
    tfidf_rank,
)

EXPECTED_CORPUS_SHA256 = "6e8a66502752debb0c2385b5654bceb85a7a046a21c5bc7bea22ae1a460a61e9"
EXPECTED_SOURCE_COMMIT = "0c8039f28fdcc08189a23c07a3437d9d2482f9c2"
EXPECTED_EMBEDDING_SNAPSHOT = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
EXPECTED_OLLAMA_DIGEST = "357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_and_validate(corpus_path: Path, predictions_path: Path) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    observed = sha256_file(corpus_path)
    if observed != EXPECTED_CORPUS_SHA256:
        raise RuntimeError(f"frozen corpus SHA mismatch: {observed}")
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    predictions = json.loads(predictions_path.read_text(encoding="utf-8"))
    if predictions.get("source_commit") != EXPECTED_SOURCE_COMMIT:
        raise RuntimeError("A-MEM source commit mismatch")
    if predictions.get("corpus_sha256") != EXPECTED_CORPUS_SHA256:
        raise RuntimeError("A-MEM prediction corpus SHA mismatch")
    if predictions.get("embedding_snapshot") != EXPECTED_EMBEDDING_SNAPSHOT:
        raise RuntimeError("embedding snapshot mismatch")
    if predictions.get("ollama_digest") != EXPECTED_OLLAMA_DIGEST:
        raise RuntimeError("Ollama digest mismatch")
    rows = predictions.get("predictions", [])
    case_ids = [case["id"] for case in corpus["cases"]]
    predicted_ids = [row["case_id"] for row in rows]
    if len(rows) != 24 or len(set(predicted_ids)) != 24 or set(predicted_ids) != set(case_ids):
        raise RuntimeError("predictions must cover exactly 24 unique frozen cases")
    mapping = {row["case_id"]: list(row["retrieved_memory_ids"]) for row in rows}
    return corpus["cases"], mapping


def make_amem_ranker(mapping: dict[str, list[str]]) -> Callable[[dict[str, Any], int], list[str]]:
    def rank(case: dict[str, Any], k: int = 5) -> list[str]:
        return list(mapping[case["id"]])[:k]
    return rank


def reciprocal_rank(case: dict[str, Any], ranker: Callable[[dict[str, Any], int], list[str]]) -> float:
    relevant = set(case["relevant_memory_ids"])
    if not relevant:
        return 0.0
    for index, memory_id in enumerate(ranker(case, 5)):
        if memory_id in relevant:
            return 1.0 / (index + 1)
    return 0.0


def win_tie_loss(cases: list[dict[str, Any]], left, right) -> dict[str, int]:
    wins = ties = losses = 0
    for case in cases:
        if not case["relevant_memory_ids"]:
            continue
        delta = reciprocal_rank(case, right) - reciprocal_rank(case, left)
        if delta > 0:
            wins += 1
        elif delta < 0:
            losses += 1
        else:
            ties += 1
    return {"right_wins": wins, "ties": ties, "right_losses": losses}


def compact(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_count": result["case_count"],
        "answerable_case_count": result["answerable_case_count"],
        "abstention_case_count": result["abstention_case_count"],
        "metrics": result["metrics"],
    }


def build(cases: list[dict[str, Any]], amem_ranker) -> dict[str, Any]:
    systems = {
        "random": random_rank,
        "tfidf_local": tfidf_rank,
        "bm25_local": bm25_rank,
        "pse_current_reconstruction": pse_current_rank,
        "pse_candidate_v1": pse_candidate_v1_rank,
        "pse_candidate_v2": pse_candidate_v2_rank,
        "a_mem_exact_run1": amem_ranker,
    }
    evaluated = {name: compact(evaluate_cases(cases, ranker)) for name, ranker in systems.items()}
    comparisons = {}
    for name in ("pse_current_reconstruction", "pse_candidate_v1", "pse_candidate_v2"):
        comparisons[f"{name}_vs_a_mem"] = {
            "bootstrap_mrr": bootstrap_mrr_delta(cases, amem_ranker, systems[name]),
            "win_tie_loss": win_tie_loss(cases, amem_ranker, systems[name]),
            "delta_definition": f"{name} minus a_mem_exact_run1",
        }
    return {
        "schema_version": "amem-pse-frozen-24-comparison-v1",
        "claim_boundary": "Observed frozen synthetic retrieval comparison only. It does not establish general algorithm parity, superiority, equivalence, non-inferiority, production readiness, or SOTA.",
        "algorithm_parity": "NO",
        "statistical_interpretation": "UNDERPOWERED; paired point estimates are descriptive.",
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "a_mem": {
            "source_commit": EXPECTED_SOURCE_COMMIT,
            "embedding_snapshot": EXPECTED_EMBEDDING_SNAPSHOT,
            "ollama_digest": EXPECTED_OLLAMA_DIGEST,
            "run": 31269598248,
        },
        "systems": evaluated,
        "paired_comparisons": comparisons,
        "sealed_final_accessed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases, mapping = load_and_validate(args.corpus, args.predictions)
    payload = build(cases, make_amem_ranker(mapping))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
