#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import sys
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


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_smoke_module() -> Any:
    path = Path(__file__).with_name("run_longmemeval_e3_smoke.py")
    spec = importlib.util.spec_from_file_location("pse_e3_smoke", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load LongMemEval split support module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_upstream_class(upstream_dir: Path):
    resolved = upstream_dir.resolve()
    if not resolved.exists():
        raise RuntimeError(f"missing upstream directory: {resolved}")
    sys.path.insert(0, str(resolved))
    module = importlib.import_module("memory_layer_robust")
    return module.RobustAgenticMemorySystem


def session_text(session: Any) -> str:
    lines = [f"Session date: {session.timestamp}"]
    lines.extend(f"{turn.role}: {turn.content}" for turn in session.turns)
    return "\n".join(lines)


def load_frozen_examples(dataset: Path, split_manifest_path: Path) -> tuple[list[Any], dict[str, Any], str]:
    from personal_state_engine.longmemeval import load_longmemeval

    dataset_sha = sha256_file(dataset)
    if dataset_sha != EXPECTED_DATASET_SHA256:
        raise RuntimeError(f"dataset SHA-256 mismatch: expected {EXPECTED_DATASET_SHA256}, got {dataset_sha}")

    split = json.loads(split_manifest_path.read_text(encoding="utf-8"))
    if split.get("source_split") != "development" or split.get("sealed_final_accessed") is not False:
        raise RuntimeError("split manifest is not an intact development-only freeze")
    if split.get("case_ids_sha256") != EXPECTED_CASE_IDS_SHA256 or split.get("sample_count") != 20:
        raise RuntimeError("frozen development case identity mismatch")
    without_self = dict(split)
    expected_self = without_self.pop("manifest_sha256", None)
    if expected_self != canonical_sha256(without_self):
        raise RuntimeError("split manifest self hash mismatch")

    smoke = load_smoke_module()
    all_examples = load_longmemeval(dataset)
    development = smoke.build_grouped_stratified_splits(all_examples, "longmemeval-e3-v1")["development"]
    development_by_id = {example.question_id: example for example in development}

    selected = []
    records_by_id = {row["case_id"]: row for row in split["records"]}
    for case_id in split["case_ids"]:
        example = development_by_id.get(case_id)
        if example is None:
            raise RuntimeError(f"frozen development case absent from pinned dataset split: {case_id}")
        record = records_by_id[case_id]
        if record["history_fingerprint"] != smoke.history_fingerprint(example):
            raise RuntimeError(f"history fingerprint mismatch: {case_id}")
        if record["question_type"] != example.question_type or bool(record["is_abstention"]) != example.is_abstention:
            raise RuntimeError(f"case metadata mismatch: {case_id}")
        selected.append(example)
    return selected, split, dataset_sha


def run_case(example: Any, upstream_class: Any, model: str, backend: str, embedding_model: str) -> dict[str, Any]:
    from personal_state_engine.strong_baseline import AMemUpstreamAdapter

    upstream = upstream_class(model_name=embedding_model, llm_backend=backend, llm_model=model)
    adapter = AMemUpstreamAdapter(upstream)
    source_by_upstream: dict[str, str] = {}
    for session in example.sessions:
        upstream_id = adapter.write_memory({"content": session_text(session), "timestamp": session.timestamp})
        source_by_upstream[str(upstream_id)] = str(session.session_id)

    retrieved = adapter.retrieve(str(example.question), k=5)
    retrieved_session_ids: list[str] = []
    for item in retrieved:
        source_id = source_by_upstream.get(str(item.memory_id))
        if source_id is None:
            raise RuntimeError(
                f"case {example.question_id}: retrieved A-MEM id {item.memory_id} cannot be mapped to a source session"
            )
        retrieved_session_ids.append(source_id)

    return {
        "case_id": example.question_id,
        "question_type": example.question_type,
        "is_abstention": bool(example.is_abstention),
        "relevant_session_ids": list(example.answer_session_ids),
        "retrieved_session_ids": retrieved_session_ids,
        "written_session_count": len(example.sessions),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run exact-pinned A-MEM retrieval on the frozen LongMemEval development subset.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--upstream-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--shard-count", type=int, required=True)
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--backend", default="ollama")
    parser.add_argument("--embedding-model", default="all-MiniLM-L6-v2")
    args = parser.parse_args()

    if args.shard_count < 1 or args.shard_index < 0 or args.shard_index >= args.shard_count:
        raise SystemExit("invalid shard configuration")

    selected, split, dataset_sha = load_frozen_examples(args.dataset, args.split_manifest)
    shard_examples = [example for index, example in enumerate(selected) if index % args.shard_count == args.shard_index]
    upstream_class = load_upstream_class(args.upstream_dir)
    predictions = [
        run_case(example, upstream_class, args.model, args.backend, args.embedding_model)
        for example in shard_examples
    ]

    payload = {
        "schema_version": "amem-longmemeval-development-shard-v1",
        "source_commit": UPSTREAM_COMMIT,
        "dataset_sha256": dataset_sha,
        "split_manifest_sha256": sha256_file(args.split_manifest),
        "case_ids_sha256": split["case_ids_sha256"],
        "model": args.model,
        "backend": args.backend,
        "embedding_model": args.embedding_model,
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "case_count": len(predictions),
        "sealed_final_accessed": False,
        "predictions": predictions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
