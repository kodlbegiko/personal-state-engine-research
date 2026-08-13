from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any

EXPECTED_DATASET_SHA256 = "2b24be0adb26d4be8c4539a3ae9619401e7a2546cd0828185eaa846b974a1b6d"
EXPECTED_CASE_COUNT = 120
EXPECTED_SHARD_COUNT = 30
UPSTREAM_COMMIT = "0c8039f28fdcc08189a23c07a3437d9d2482f9c2"
EXPECTED_MODEL = "qwen2.5:3b"


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
    memories = list(case["memories"])
    if not memories:
        return {"case_id": case["id"], "retrieved_memory_ids": [], "written_memory_count": 0}

    upstream = upstream_class(model_name=embedding_model, llm_backend=backend, llm_model=model)
    source_by_upstream: dict[str, str] = {}
    for memory in memories:
        kwargs: dict[str, Any] = {}
        if "timestamp" in memory:
            kwargs["time"] = memory["timestamp"]
        upstream_id = upstream.add_note(str(memory["text"]), **kwargs)
        source_by_upstream[str(upstream_id)] = str(memory["id"])

    _, indices = upstream.find_related_memories(str(case["query"]), k=5)
    ordered = list(upstream.memories.values())
    source_ids: list[str] = []
    for index in indices:
        if index < 0 or index >= len(ordered):
            raise RuntimeError(f"case {case['id']}: out-of-range memory index {index}")
        upstream_id = str(ordered[index].id)
        source_id = source_by_upstream.get(upstream_id)
        if source_id is None:
            raise RuntimeError(f"case {case['id']}: unknown upstream memory id {upstream_id}")
        source_ids.append(source_id)
    return {
        "case_id": str(case["id"]),
        "retrieved_memory_ids": source_ids,
        "written_memory_count": len(memories),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--upstream-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--shard-count", type=int, required=True)
    parser.add_argument("--model", default=EXPECTED_MODEL)
    parser.add_argument("--backend", default="ollama")
    parser.add_argument("--embedding-model", required=True)
    args = parser.parse_args()

    if args.shard_count != EXPECTED_SHARD_COUNT or not 0 <= args.shard_index < EXPECTED_SHARD_COUNT:
        raise SystemExit("clean Stage2 requires exactly 30 deterministic shards")
    if args.model != EXPECTED_MODEL or args.backend != "ollama":
        raise SystemExit("exact A-MEM model/backend identity mismatch")
    observed_sha = sha256_file(args.corpus)
    if observed_sha != EXPECTED_DATASET_SHA256:
        raise SystemExit(f"fresh clean corpus SHA mismatch: {observed_sha}")

    cases = json.loads(args.corpus.read_text(encoding="utf-8"))
    if len(cases) != EXPECTED_CASE_COUNT or len({str(c["id"]) for c in cases}) != EXPECTED_CASE_COUNT:
        raise SystemExit("clean corpus must contain exactly 120 unique cases")
    shard_cases = [case for i, case in enumerate(cases) if i % args.shard_count == args.shard_index]
    if len(shard_cases) != 4:
        raise SystemExit(f"expected 4 cases in shard {args.shard_index}, got {len(shard_cases)}")

    upstream_class = load_upstream_class(args.upstream_dir)
    predictions = [run_case(case, upstream_class, args.model, args.backend, args.embedding_model) for case in shard_cases]
    result = {
        "schema_version": "clean-lineage-exact-amem-shard-v1",
        "source_commit": UPSTREAM_COMMIT,
        "dataset_sha256": observed_sha,
        "model": args.model,
        "backend": args.backend,
        "embedding_model": args.embedding_model,
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "case_count": len(predictions),
        "new_monetary_cost_usd": 0.0,
        "paid_api_used": False,
        "paid_gpu_used": False,
        "sealed_surface_operation_performed": False,
        "predictions": predictions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
