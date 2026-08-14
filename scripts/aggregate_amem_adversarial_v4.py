#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Callable

EXPECTED_CORPUS_SHA256 = "02e3afef1e17d9d8991ea7172cbfc19ad239874c914a088c20e5de6a146f7a1d"
EXPECTED_CASE_COUNT = 24
UPSTREAM_COMMIT = "0c8039f28fdcc08189a23c07a3437d9d2482f9c2"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_time(path: Path) -> dict[str, float | int | None]:
    text = path.read_text(encoding="utf-8", errors="replace")
    wall = re.search(r"Elapsed \(wall clock\) time.*?:\s*(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)", text)
    rss = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", text)
    wall_seconds = None
    if wall:
        wall_seconds = int(wall.group(1) or 0) * 3600 + int(wall.group(2)) * 60 + float(wall.group(3))
    return {"wall_seconds": wall_seconds, "peak_rss_kib": int(rss.group(1)) if rss else None}


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
    return next((1.0 / (i + 1) for i, memory_id in enumerate(ranker(case, 5)) if memory_id in relevant), 0.0)


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
        bm25_rank,
        bootstrap_mrr_delta,
        evaluate_cases,
        pse_candidate_v1_rank,
        pse_current_rank,
        random_rank,
        recency_rank,
        tfidf_rank,
    )

    parser = argparse.ArgumentParser(description="Aggregate exact A-MEM adversarial-v4 shards and compare frozen systems.")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--shards", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--embedding-snapshot", required=True)
    parser.add_argument("--ollama-digest", required=True)
    args = parser.parse_args()

    if sha256_file(args.corpus) != EXPECTED_CORPUS_SHA256:
        raise SystemExit("v4 corpus SHA mismatch")
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if protocol.get("status") != "FROZEN_BEFORE_A_MEM_V4_RESULTS" or protocol.get("integrity", {}).get("sealed_final_accessed") is not False:
        raise SystemExit("A-MEM v4 protocol is not intact")
    if protocol["benchmark"]["scope"] != "ALL_CASES" or protocol["benchmark"]["sha256"] != EXPECTED_CORPUS_SHA256:
        raise SystemExit("A-MEM v4 protocol scope/hash mismatch")
    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    cases = list(corpus.get("cases", []))
    expected_ids = [case["id"] for case in cases]
    if len(cases) != EXPECTED_CASE_COUNT or len(set(expected_ids)) != EXPECTED_CASE_COUNT:
        raise SystemExit("v4 corpus must contain exactly 24 unique cases")

    shard_files = sorted(args.shards.glob("shard-*.json"))
    if len(shard_files) != 8:
        raise SystemExit(f"expected 8 shard files, found {len(shard_files)}")
    predictions: list[dict[str, Any]] = []
    shard_meta = []
    for path in shard_files:
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("source_commit") != UPSTREAM_COMMIT or row.get("corpus_sha256") != EXPECTED_CORPUS_SHA256:
            raise SystemExit(f"provenance mismatch in {path}")
        if row.get("sealed_final_accessed") is not False or float(row.get("new_monetary_cost_usd", -1)) != 0.0:
            raise SystemExit(f"integrity/cost mismatch in {path}")
        if row.get("protocol_sha256") != sha256_file(args.protocol):
            raise SystemExit(f"protocol mismatch in {path}")
        predictions.extend(row["predictions"])
        usage_path = args.shards / f"time-shard-{row['shard_index']}.txt"
        usage = parse_time(usage_path) if usage_path.exists() else {"wall_seconds": None, "peak_rss_kib": None}
        shard_meta.append({"shard_index": row["shard_index"], "case_count": row["case_count"], **usage})
    ids = [row["case_id"] for row in predictions]
    if len(ids) != 24 or len(set(ids)) != 24 or set(ids) != set(expected_ids):
        raise SystemExit("A-MEM v4 output contains missing, duplicate, or extra cases")
    order = {case_id: i for i, case_id in enumerate(expected_ids)}
    predictions.sort(key=lambda row: order[row["case_id"]])
    prediction_by_id = {row["case_id"]: list(row["retrieved_memory_ids"]) for row in predictions}

    def amem_rank(case: dict[str, Any], k: int = 5) -> list[str]:
        return prediction_by_id[case["id"]][:k]

    systems: dict[str, Callable[[dict[str, Any], int], list[str]]] = {
        "pse_current_reconstruction": pse_current_rank,
        "pse_candidate_v1": pse_candidate_v1_rank,
        "pse_candidate_v2": pse_candidate_v2_rank,
        "a_mem_exact": amem_rank,
        "bm25_local": bm25_rank,
        "tfidf_local": tfidf_rank,
        "random": random_rank,
        "recency": recency_rank,
    }
    comparison = {
        "schema_version": "amem-adversarial-v4-full-comparison-v1",
        "run_id": int(args.run_id),
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "protocol_sha256": sha256_file(args.protocol),
        "case_count": 24,
        "answerable_case_count": 22,
        "abstention_case_count": 2,
        "systems": {name: normalize(evaluate_cases(cases, ranker)) for name, ranker in systems.items()},
        "paired_statistics": {
            "a_mem_vs_pse_current": {**bootstrap_mrr_delta(cases, pse_current_rank, amem_rank), "win_tie_loss": win_tie_loss(cases, pse_current_rank, amem_rank), "right_system": "a_mem_exact"},
            "a_mem_vs_pse_candidate_v1": {**bootstrap_mrr_delta(cases, pse_candidate_v1_rank, amem_rank), "win_tie_loss": win_tie_loss(cases, pse_candidate_v1_rank, amem_rank), "right_system": "a_mem_exact"},
            "a_mem_vs_pse_candidate_v2": {**bootstrap_mrr_delta(cases, pse_candidate_v2_rank, amem_rank), "win_tie_loss": win_tie_loss(cases, pse_candidate_v2_rank, amem_rank), "right_system": "a_mem_exact"},
            "pse_candidate_v2_vs_a_mem": {**bootstrap_mrr_delta(cases, amem_rank, pse_candidate_v2_rank), "win_tie_loss": win_tie_loss(cases, amem_rank, pse_candidate_v2_rank), "right_system": "pse_candidate_v2"},
        },
        "statistical_interpretation": "UNDERPOWERED: n=22 answerable is below the preregistered n=30 threshold; paired intervals are descriptive.",
        "algorithm_parity": "NO",
        "operator_designed": True,
        "independent_reproduction": False,
        "sealed_final_accessed": False,
        "new_monetary_cost_usd": 0.0,
        "claim_boundary": protocol["claim_boundary"],
    }

    walls = [float(row["wall_seconds"]) for row in shard_meta if row["wall_seconds"] is not None]
    rss = [int(row["peak_rss_kib"]) for row in shard_meta if row["peak_rss_kib"] is not None]
    resources = {
        "schema_version": "amem-adversarial-v4-resource-v1",
        "run_id": int(args.run_id),
        "source_commit": UPSTREAM_COMMIT,
        "embedding_snapshot": args.embedding_snapshot,
        "ollama_digest": args.ollama_digest,
        "serialized_inference_wall_seconds": sum(walls) if walls else None,
        "mean_end_to_end_case_wall_seconds": (sum(walls) / 24) if walls else None,
        "max_shard_wall_seconds": max(walls) if walls else None,
        "max_peak_rss_kib": max(rss) if rss else None,
        "pure_query_latency_ms": None,
        "pure_query_latency_status": "NOT_SEPARATELY_MEASURED",
        "shards": shard_meta,
        "new_monetary_cost_usd": 0.0,
        "paid_api_used": False,
        "cloud_gpu_used": False,
        "sealed_final_accessed": False,
    }

    output = args.output_root
    output.mkdir(parents=True, exist_ok=True)
    predictions_payload = {
        "schema_version": "amem-adversarial-v4-predictions-v1",
        "run_id": int(args.run_id),
        "source_commit": UPSTREAM_COMMIT,
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "protocol_sha256": sha256_file(args.protocol),
        "embedding_snapshot": args.embedding_snapshot,
        "ollama_digest": args.ollama_digest,
        "case_count": 24,
        "predictions": predictions,
        "sealed_final_accessed": False,
        "new_monetary_cost_usd": 0.0,
    }
    write_json(output / "predictions-run1.json", predictions_payload)
    write_json(output / "comparison-run1.json", comparison)
    write_json(output / "resource-summary-run1.json", resources)
    artifact_paths = [output / "predictions-run1.json", output / "comparison-run1.json", output / "resource-summary-run1.json"]
    registry = {
        "schema_version": "amem-adversarial-v4-artifact-registry-v1",
        "source_run_id": int(args.run_id),
        "source_commit": UPSTREAM_COMMIT,
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "protocol_sha256": sha256_file(args.protocol),
        "artifact_count": len(artifact_paths),
        "new_monetary_cost_usd": 0.0,
        "sealed_final_accessed": False,
        "artifacts": [{
            "path": path.as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "source_workflow_run": int(args.run_id),
            "generation_command": "python scripts/aggregate_amem_adversarial_v4.py ...",
        } for path in artifact_paths],
    }
    write_json(output / "artifact-registry.json", registry)
    print(json.dumps({"status": "AMEM_ADVERSARIAL_V4_COMPLETE", "run_id": int(args.run_id), "a_mem": comparison["systems"]["a_mem_exact"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
