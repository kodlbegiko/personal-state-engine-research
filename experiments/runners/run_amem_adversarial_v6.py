#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any

EXPECTED_CORPUS_SHA256 = "d5ff2fa4c51ebf09c42c710cd6a8bcf8445060858abf07ed1b34a7ac940471b0"
EXPECTED_PROTOCOL_SHA256 = "d6948b2ecb86f651cd23cbaed30f6884d3ea14526f6272ca039b3ed88c7963c2"
EXPECTED_CASE_COUNT = 90
EXPECTED_SHARD_COUNT = 30
UPSTREAM_COMMIT = "0c8039f28fdcc08189a23c07a3437d9d2482f9c2"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
            event["timestamp"] = memory["timestamp"]
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
    parser = argparse.ArgumentParser(description="Run exact-pinned A-MEM on frozen adversarial-v6 confirmatory cases.")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--upstream-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--shard-count", type=int, required=True)
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--backend", default="ollama")
    parser.add_argument("--embedding-model", required=True)
    args = parser.parse_args()

    if args.shard_count != EXPECTED_SHARD_COUNT or not (0 <= args.shard_index < args.shard_count):
        raise SystemExit(f"v6 protocol requires exactly {EXPECTED_SHARD_COUNT} deterministic shards")
    corpus_sha = sha256_file(args.corpus)
    if corpus_sha != EXPECTED_CORPUS_SHA256:
        raise SystemExit(f"v6 corpus SHA mismatch: {corpus_sha}")
    protocol_sha = sha256_file(args.protocol)
    if protocol_sha != EXPECTED_PROTOCOL_SHA256:
        raise SystemExit(f"v6 protocol SHA mismatch: {protocol_sha}")
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if protocol.get("status") != "FROZEN_BEFORE_STAGE1_SYSTEM_EXECUTION":
        raise SystemExit("v6 protocol is not frozen")
    benchmark = protocol.get("benchmark", {})
    if benchmark.get("dataset_sha256") != EXPECTED_CORPUS_SHA256 or benchmark.get("post_result_editing_allowed") is not False:
        raise SystemExit("v6 benchmark identity/integrity mismatch")
    stage2 = protocol.get("stage2_exact_a_mem", {})
    identity = stage2.get("identity", {})
    if stage2.get("authorized_only_if_stage1_discrimination_passes") is not True:
        raise SystemExit("v6 stage2 authorization rule mismatch")
    if identity.get("commit") != UPSTREAM_COMMIT or identity.get("model") != "qwen2.5:3b":
        raise SystemExit("A-MEM v6 identity mismatch")
    if stage2.get("expected_case_count") != EXPECTED_CASE_COUNT or float(stage2.get("new_monetary_cost_usd", -1)) != 0.0:
        raise SystemExit("A-MEM v6 scope/cost mismatch")
    integrity = protocol.get("gate_e_integrity_requirements", {})
    if integrity.get("zero_paid_resources") is not True or integrity.get("fail_closed") is not True:
        raise SystemExit("v6 integrity contract mismatch")

    payload = json.loads(args.corpus.read_text(encoding="utf-8"))
    cases = list(payload.get("cases", []))
    ids = [str(case["id"]) for case in cases]
    if len(cases) != EXPECTED_CASE_COUNT or len(set(ids)) != EXPECTED_CASE_COUNT:
        raise SystemExit("v6 corpus must contain exactly 90 unique cases")
    shard_cases = [case for index, case in enumerate(cases) if index % args.shard_count == args.shard_index]
    if len(shard_cases) != 3:
        raise SystemExit(f"expected 3 cases in shard {args.shard_index}, found {len(shard_cases)}")

    upstream_class = load_upstream_class(args.upstream_dir)
    predictions = [run_case(case, upstream_class, args.model, args.backend, args.embedding_model) for case in shard_cases]
    result = {
        "schema_version": "amem-adversarial-v6-shard-v1",
        "source_commit": UPSTREAM_COMMIT,
        "corpus_sha256": corpus_sha,
        "protocol_sha256": protocol_sha,
        "model": args.model,
        "backend": args.backend,
        "embedding_model": args.embedding_model,
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "case_count": len(predictions),
        "sealed_final_accessed": False,
        "new_monetary_cost_usd": 0.0,
        "predictions": predictions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
