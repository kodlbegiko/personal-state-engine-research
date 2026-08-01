#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def load_smoke_module() -> Any:
    path = Path(__file__).with_name("run_longmemeval_e3_smoke.py")
    spec = importlib.util.spec_from_file_location("pse_e3_smoke", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load E3 support module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def serialize_example(example: Any) -> dict[str, object]:
    return {
        "question_id": example.question_id,
        "question_type": example.question_type,
        "question": example.question,
        "answer": example.answer,
        "question_date": example.question_date,
        "haystack_session_ids": [session.session_id for session in example.sessions],
        "haystack_dates": [session.timestamp for session in example.sessions],
        "haystack_sessions": [
            [
                {
                    "role": turn.role,
                    "content": turn.content,
                    "has_answer": bool(turn.has_answer),
                }
                for turn in session.turns
            ]
            for session in example.sessions
        ],
        "answer_session_ids": list(example.answer_session_ids),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract the frozen matrix cases and non-overlapping screening cases from pinned LongMemEval-S.")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    from personal_state_engine.longmemeval import load_longmemeval

    args = parse_args()
    source = json.loads(args.source_manifest.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    split = json.loads(args.split_manifest.read_text(encoding="utf-8"))
    dataset_hash = sha256_file(args.dataset)
    if dataset_hash != source["expected_sha256"] or dataset_hash != protocol["dataset"]["sha256"]:
        raise RuntimeError("pinned dataset hash mismatch")
    if args.dataset.stat().st_size != int(source["expected_size_bytes"]):
        raise RuntimeError("pinned dataset size mismatch")

    smoke = load_smoke_module()
    all_examples = load_longmemeval(args.dataset)
    development = smoke.build_grouped_stratified_splits(
        all_examples, protocol["selection"]["parent_split_seed"]
    )["development"]
    development_by_id = {example.question_id: example for example in development}
    selected_ids = list(split["case_ids"])
    if any(case_id not in development_by_id for case_id in selected_ids):
        raise RuntimeError("frozen case absent from development split")
    selected_set = set(selected_ids)
    screening_candidates = [example for example in development if example.question_id not in selected_set]
    screening = sorted(
        screening_candidates,
        key=lambda example: hashlib.sha256(
            f"model-screen-v1|{example.question_id}".encode("utf-8")
        ).hexdigest(),
    )[:2]
    if len(screening) != 2:
        raise RuntimeError("unable to select two non-overlapping screening cases")

    execution_examples = [development_by_id[case_id] for case_id in selected_ids] + screening
    payload = [serialize_example(example) for example in execution_examples]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    manifest: dict[str, object] = {
        "schema_version": "longmemeval-execution-subset-v1",
        "source_dataset_sha256": dataset_hash,
        "source_dataset_size_bytes": args.dataset.stat().st_size,
        "protocol_sha256": sha256_file(args.protocol),
        "split_manifest_sha256": sha256_file(args.split_manifest),
        "formal_case_ids": selected_ids,
        "screening_case_ids": [example.question_id for example in screening],
        "formal_case_count": len(selected_ids),
        "screening_case_count": len(screening),
        "total_case_count": len(payload),
        "formal_and_screening_disjoint": selected_set.isdisjoint(
            {example.question_id for example in screening}
        ),
        "sealed_final_accessed": False,
        "selection_rule": "frozen 20 formal cases plus two deterministic hash-ranked non-overlapping development screening cases",
        "execution_subset_sha256": sha256_file(args.output),
        "execution_subset_size_bytes": args.output.stat().st_size,
        "history_fingerprint_sha256": canonical_sha256(
            [smoke.history_fingerprint(example) for example in execution_examples]
        ),
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output_manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "EXTRACTED_AND_VERIFIED",
                "formal_cases": len(selected_ids),
                "screening_cases": len(screening),
                "execution_subset_sha256": manifest["execution_subset_sha256"],
                "output": args.output.as_posix(),
                "manifest": args.output_manifest.as_posix(),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
