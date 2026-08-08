#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any

EXPECTED_CORPUS_SHA256 = "7e23df3b4f1bdac6b8999ffe56bea97dcd825fb5ab8536a3acec1ea702aded56"
EXPECTED_CASE_COUNT = 12
UPSTREAM_COMMIT = "0c8039f28fdcc08189a23c07a3437d9d2482f9c2"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select_cases(cases: list[dict[str, Any]], shard_index: int, shard_count: int) -> list[dict[str, Any]]:
    if shard_count < 1 or shard_index < 0 or shard_index >= shard_count:
        raise ValueError("invalid shard configuration")
    return [case for index, case in enumerate(cases) if index % shard_count == shard_index]


def load_upstream_class(upstream_dir: Path):
    resolved = upstream_dir.resolve()
    if not resolved.exists():
        raise RuntimeError(f"missing upstream directory: {resolved}")
    sys.path.insert(0, str(resolved))
    module = importlib.import_module("memory_layer_robust")
    return module.RobustAgenticMemorySystem


def run_case(case: dict[str, Any], upstream_class: Any, model: str, backend: str, embedding_model: str) -> dict[str, Any]:
    from personal_state_engine.strong_baseline import AMemUpstreamAdapter

    memories = list(case["memories"])
    if not memories:
        return {
            "case_id": case["id"],
            "retrieved_memory_ids": [],
            "written_memory_count": 0,
            "is_abstention": not bool(case["relevant_memory_ids"]),
        }
    upstream = upstream_class(model_name=embedding_model, llm_backend=backend, llm_model=model)
    adapter = AMemUpstreamAdapter(upstream)
    source_by_upstream: dict[str, str] = {}
    for memory in memories:
        event: dict[str, Any] = {"content": memory["text"]}
        if "timestamp" in memory:
            event["timestamp"] = memory.get("timestamp")
        upstream_id = adapter.write_memory(event)
        source_by_upstream[str(upstream_id)] = str(memory["id"])
    retrieved = adapter.retrieve(str(case["query"]), k=5)
    source_ids: list[str] = []
    for item in retrieved:
        source_id = source_by_upstream.get(str(item.memory_id))
        if source_id is None:
            raise RuntimeError(f"case {case['id']}: unknown upstream memory id {item.memory_id}")
        source_ids.append(source_id)
    return {
        "case_id": case["id"],
        "retrieved_memory_ids": source_ids,
        "written_memory_count": len(memories),
        "is_abstention": not bool(case["relevant_memory_ids"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run exact-pinned A-MEM on the complete frozen adversarial-v3 withheld set.")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--upstream-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--shard-count", type=int, required=True)
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--backend", default="ollama")
    parser.add_argument("--embedding-model", default="all-MiniLM-L6-v2")
    args = parser.parse_args()

    observed_sha = sha256_file(args.corpus)
    if observed_sha != EXPECTED_CORPUS_SHA256:
        raise SystemExit(f"withheld corpus SHA mismatch: expected {EXPECTED_CORPUS_SHA256}, got {observed_sha}")
    payload = json.loads(args.corpus.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    if len(cases) != EXPECTED_CASE_COUNT or len({case["id"] for case in cases}) != EXPECTED_CASE_COUNT:
        raise SystemExit("withheld corpus must contain exactly 12 unique cases")

    shard_cases = select_cases(cases, args.shard_index, args.shard_count)
    upstream_class = load_upstream_class(args.upstream_dir)
    predictions = [run_case(case, upstream_class, args.model, args.backend, args.embedding_model) for case in shard_cases]
    result = {
        "schema_version": "amem-adversarial-v3-withheld-shard-v1",
        "source_commit": UPSTREAM_COMMIT,
        "corpus_sha256": observed_sha,
        "model": args.model,
        "backend": args.backend,
        "embedding_model": args.embedding_model,
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "case_count": len(shard_cases),
        "sealed_final_accessed": False,
        "new_monetary_cost_usd": 0.0,
        "predictions": predictions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
