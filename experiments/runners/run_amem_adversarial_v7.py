from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any

EXPECTED_CORPUS_SHA256 = "77f2113fdf67001c53a31f0d9eff4ecac7e71564335ab9a505665b44a05546cd"
EXPECTED_PROTOCOL_SHA256 = "d2c0b23c467175e54d325d019afaf555f5d26f09a4320aae61eee9cd65f4fdd3"
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
        return {"case_id": case["id"], "retrieved_memory_ids": [], "written_memory_count": 0}
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
    return {"case_id": case["id"], "retrieved_memory_ids": source_ids, "written_memory_count": len(memories)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run exact-pinned A-MEM on frozen adversarial-v7 cases.")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--upstream-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--shard-count", type=int, required=True)
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--backend", default="ollama")
    parser.add_argument("--embedding-model", required=True)
    args = parser.parse_args()

    if args.shard_count != EXPECTED_SHARD_COUNT or not (0 <= args.shard_index < args.shard_count):
        raise SystemExit(f"v7 protocol requires exactly {EXPECTED_SHARD_COUNT} deterministic shards")
    corpus_sha = sha256_file(args.corpus)
    protocol_sha = sha256_file(args.protocol)
    if corpus_sha != EXPECTED_CORPUS_SHA256:
        raise SystemExit(f"v7 corpus SHA mismatch: {corpus_sha}")
    if protocol_sha != EXPECTED_PROTOCOL_SHA256:
        raise SystemExit(f"v7 protocol SHA mismatch: {protocol_sha}")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if manifest.get("status") != "FROZEN_BEFORE_ANY_SYSTEM_EXECUTION":
        raise SystemExit("v7 benchmark is not frozen")
    if manifest.get("dataset_sha256") != corpus_sha or manifest.get("evaluation_protocol_sha256") != protocol_sha:
        raise SystemExit("v7 manifest identity mismatch")
    if manifest.get("post_result_editing_allowed") is not False:
        raise SystemExit("v7 post-result editing policy mismatch")
    stage2 = protocol.get("stage2_exact_a_mem", {})
    identity = stage2.get("identity", {})
    if identity.get("commit") != UPSTREAM_COMMIT or identity.get("model") != "qwen2.5:3b":
        raise SystemExit("A-MEM v7 identity mismatch")
    if stage2.get("expected_case_count") != EXPECTED_CASE_COUNT or float(stage2.get("new_monetary_cost_usd", -1)) != 0.0:
        raise SystemExit("A-MEM v7 scope/cost mismatch")
    if protocol.get("integrity", {}).get("zero_paid_resources") is not True or protocol.get("integrity", {}).get("fail_closed") is not True:
        raise SystemExit("v7 integrity contract mismatch")

    payload = json.loads(args.corpus.read_text(encoding="utf-8"))
    cases = list(payload.get("cases", []))
    ids = [str(case["id"]) for case in cases]
    if len(cases) != EXPECTED_CASE_COUNT or len(set(ids)) != EXPECTED_CASE_COUNT:
        raise SystemExit("v7 corpus must contain exactly 90 unique cases")
    shard_cases = [case for index, case in enumerate(cases) if index % args.shard_count == args.shard_index]
    if len(shard_cases) != 3:
        raise SystemExit(f"expected 3 cases in shard {args.shard_index}, found {len(shard_cases)}")

    upstream_class = load_upstream_class(args.upstream_dir)
    predictions = [run_case(case, upstream_class, args.model, args.backend, args.embedding_model) for case in shard_cases]
    result = {
        "schema_version": "amem-adversarial-v7-shard-v1",
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
