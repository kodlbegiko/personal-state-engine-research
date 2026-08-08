#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

EXPECTED_DATASET_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
EXPECTED_CASE_IDS_SHA256 = "519b4db13813b60ad6a49cce919543b0639524a98bd1b0d1615c53e62cf8cc7e"
UPSTREAM_COMMIT = "0c8039f28fdcc08189a23c07a3437d9d2482f9c2"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def dcg(relevances: list[int]) -> float:
    return sum(rel / math.log2(rank + 2) for rank, rel in enumerate(relevances))


def metrics_for_case(relevant: set[str], retrieved: list[str]) -> dict[str, float]:
    def recall_at(k: int) -> float:
        if not relevant:
            return 1.0 if not retrieved[:k] else 0.0
        return len(relevant.intersection(retrieved[:k])) / len(relevant)

    def precision_at(k: int) -> float:
        if not relevant:
            return 1.0 if not retrieved[:k] else 0.0
        return sum(item in relevant for item in retrieved[:k]) / k

    rr = 0.0
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant:
            rr = 1.0 / rank
            break
    observed = [1 if item in relevant else 0 for item in retrieved[:5]]
    ideal = [1] * min(len(relevant), 5)
    ideal_dcg = dcg(ideal)
    ndcg = 1.0 if not relevant and not retrieved[:5] else (dcg(observed) / ideal_dcg if ideal_dcg else 0.0)
    irrelevant_rate = 0.0 if not retrieved else sum(item not in relevant for item in retrieved) / len(retrieved)
    return {
        "recall_at_1": recall_at(1),
        "recall_at_3": recall_at(3),
        "recall_at_5": recall_at(5),
        "precision_at_1": precision_at(1),
        "precision_at_3": precision_at(3),
        "precision_at_5": precision_at(5),
        "mrr": rr,
        "ndcg_at_5": ndcg,
        "irrelevant_retrieval_rate": irrelevant_rate,
    }


def mean_metrics(rows: list[dict[str, float]]) -> dict[str, float]:
    if not rows:
        return {}
    return {key: sum(row[key] for row in rows) / len(rows) for key in rows[0]}


def parse_time(path: Path) -> dict[str, float | int | None]:
    text = path.read_text(encoding="utf-8", errors="replace")
    wall = re.search(r"Elapsed \(wall clock\) time.*?:\s*(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)", text)
    rss = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", text)
    wall_seconds = None
    if wall:
        hours = int(wall.group(1) or 0)
        wall_seconds = hours * 3600 + int(wall.group(2)) * 60 + float(wall.group(3))
    return {"wall_seconds": wall_seconds, "peak_rss_kib": int(rss.group(1)) if rss else None}


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate fail-closed A-MEM LongMemEval development shards.")
    parser.add_argument("--shards", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--embedding-snapshot", required=True)
    parser.add_argument("--ollama-digest", required=True)
    args = parser.parse_args()

    split = json.loads(args.split_manifest.read_text(encoding="utf-8"))
    expected_ids = list(split["case_ids"])
    if split.get("case_ids_sha256") != EXPECTED_CASE_IDS_SHA256 or split.get("sample_count") != 20:
        raise SystemExit("frozen case identity mismatch")

    predictions: list[dict[str, Any]] = []
    shard_meta = []
    shard_files = sorted(args.shards.glob("shard-*.json"))
    if not shard_files:
        raise SystemExit("no shard outputs found")
    for path in shard_files:
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("source_commit") != UPSTREAM_COMMIT:
            raise SystemExit(f"A-MEM source mismatch in {path}")
        if row.get("dataset_sha256") != EXPECTED_DATASET_SHA256:
            raise SystemExit(f"dataset mismatch in {path}")
        if row.get("case_ids_sha256") != EXPECTED_CASE_IDS_SHA256:
            raise SystemExit(f"case-id freeze mismatch in {path}")
        if row.get("sealed_final_accessed") is not False:
            raise SystemExit(f"sealed-final flag violated in {path}")
        predictions.extend(row["predictions"])
        time_path = args.shards / f"time-shard-{row['shard_index']}.txt"
        usage = parse_time(time_path) if time_path.exists() else {"wall_seconds": None, "peak_rss_kib": None}
        shard_meta.append({
            "shard_index": row["shard_index"],
            "case_count": row["case_count"],
            **usage,
        })

    ids = [row["case_id"] for row in predictions]
    if len(ids) != 20 or len(set(ids)) != 20 or set(ids) != set(expected_ids):
        raise SystemExit(f"incomplete/duplicate/extra cases: {len(ids)} rows, {len(set(ids))} unique")
    order = {case_id: index for index, case_id in enumerate(expected_ids)}
    predictions.sort(key=lambda row: order[row["case_id"]])

    details = []
    answerable_metrics = []
    all_metrics = []
    abstention_total = 0
    abstention_correct = 0
    false_retrieval = 0
    for prediction in predictions:
        relevant = set(prediction["relevant_session_ids"])
        retrieved = list(prediction["retrieved_session_ids"])
        metrics = metrics_for_case(relevant, retrieved)
        all_metrics.append(metrics)
        if relevant:
            answerable_metrics.append(metrics)
        else:
            abstention_total += 1
            correct = not retrieved
            abstention_correct += int(correct)
            false_retrieval += int(bool(retrieved))
        details.append({"case_id": prediction["case_id"], **metrics})

    output = args.output_root
    output.mkdir(parents=True, exist_ok=True)
    predictions_payload = {
        "schema_version": "amem-longmemeval-development-predictions-v1",
        "run_id": args.run_id,
        "source_commit": UPSTREAM_COMMIT,
        "dataset_sha256": EXPECTED_DATASET_SHA256,
        "split_manifest_sha256": sha256_file(args.split_manifest),
        "case_ids_sha256": EXPECTED_CASE_IDS_SHA256,
        "embedding_snapshot": args.embedding_snapshot,
        "ollama_digest": args.ollama_digest,
        "case_count": 20,
        "sealed_final_accessed": False,
        "predictions": predictions,
    }
    write_json(output / "predictions-run1.json", predictions_payload)

    metrics_payload = {
        "schema_version": "amem-longmemeval-development-retrieval-results-v1",
        "run_id": args.run_id,
        "case_count": 20,
        "answerable_case_count": len(answerable_metrics),
        "abstention_case_count": abstention_total,
        "aggregate_all_cases": mean_metrics(all_metrics),
        "aggregate_answerable_cases": mean_metrics(answerable_metrics),
        "abstention_accuracy": abstention_correct / abstention_total if abstention_total else None,
        "false_retrieval_rate_on_abstention": false_retrieval / abstention_total if abstention_total else None,
        "details": details,
        "claim_limit": "Development retrieval evidence only; not end-to-end D4 completion, parity, superiority, equivalence, or sealed-final evidence.",
    }
    write_json(output / "retrieval-results-run1.json", metrics_payload)

    walls = [float(row["wall_seconds"]) for row in shard_meta if row["wall_seconds"] is not None]
    rss = [int(row["peak_rss_kib"]) for row in shard_meta if row["peak_rss_kib"] is not None]
    resources = {
        "schema_version": "amem-longmemeval-development-resource-run1-v1",
        "run_id": args.run_id,
        "source_commit": UPSTREAM_COMMIT,
        "dataset_sha256": EXPECTED_DATASET_SHA256,
        "embedding_snapshot": args.embedding_snapshot,
        "ollama_digest": args.ollama_digest,
        "sharding": f"{len(shard_meta)} independent deterministic case shards; no algorithm change",
        "serialized_inference_wall_seconds": sum(walls) if walls else None,
        "max_shard_wall_seconds": max(walls) if walls else None,
        "max_peak_rss_kib": max(rss) if rss else None,
        "shards": shard_meta,
        "paid_api_cost_usd": 0.0,
        "cloud_gpu_cost_usd": 0.0,
        "new_monetary_cost_usd": 0.0,
        "sealed_final_accessed": False,
    }
    write_json(output / "resource-summary-run1.json", resources)

    artifact_paths = [
        output / "predictions-run1.json",
        output / "retrieval-results-run1.json",
        output / "resource-summary-run1.json",
    ]
    registry = {
        "schema_version": "amem-longmemeval-development-artifact-registry-v1",
        "source_run_id": int(args.run_id),
        "artifact_count": len(artifact_paths),
        "source_commit": UPSTREAM_COMMIT,
        "dataset_sha256": EXPECTED_DATASET_SHA256,
        "case_ids_sha256": EXPECTED_CASE_IDS_SHA256,
        "embedding_snapshot": args.embedding_snapshot,
        "ollama_digest": args.ollama_digest,
        "paid_api_cost_usd": 0.0,
        "cloud_gpu_cost_usd": 0.0,
        "sealed_final_accessed": False,
        "artifacts": [
            {"path": path.as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in artifact_paths
        ],
    }
    write_json(output / "artifact-registry.json", registry)
    print(json.dumps({"status": "AMEM_DEVELOPMENT_RETRIEVAL_AGGREGATED", "run_id": args.run_id, "metrics": metrics_payload["aggregate_answerable_cases"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
