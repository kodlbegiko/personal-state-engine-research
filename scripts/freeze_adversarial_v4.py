#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

EXPECTED_CATEGORIES = {
    "lexical_copy_distractor",
    "keyword_stuffing",
    "wrong_entity_high_overlap",
    "stale_high_overlap",
    "contradictory_high_overlap",
    "same_name_entity_confusion",
    "fresh_irrelevant_memory",
    "duplicate_irrelevant_cluster",
    "partial_truth_distractor",
    "revoked_preference",
    "superseded_project_status",
    "ambiguous_no_evidence",
}
CANDIDATE_V2_FREEZE_COMMIT = "d627f61d0888306a97f3ef0b78aa29dc00c444bb"
CANDIDATE_V2_SOURCE_COMMIT = "52c8341e4317a1492ec5511907414c7deee77ef6"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and freeze post-candidate adversarial-v4 discrimination corpus.")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()

    payload: dict[str, Any] = json.loads(args.corpus.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "pse-adversarial-v4-postfreeze-v1":
        raise SystemExit("unexpected adversarial-v4 schema")
    design = payload.get("design", {})
    if design.get("sealed_final_accessed") is not False or design.get("candidate_tuning_after_generation") is not False:
        raise SystemExit("integrity boundary violated")
    cases = payload.get("cases", [])
    if len(cases) != 24 or len({case.get("id") for case in cases}) != 24:
        raise SystemExit("adversarial-v4 must contain exactly 24 unique cases")
    categories = Counter(case.get("category") for case in cases)
    if set(categories) != EXPECTED_CATEGORIES or any(categories[category] != 2 for category in EXPECTED_CATEGORIES):
        raise SystemExit(f"category balance mismatch: {categories}")

    answerable = 0
    abstention = 0
    case_rows = []
    for case in cases:
        memories = case.get("memories", [])
        ids = [memory.get("id") for memory in memories]
        if len(memories) != 10 or len(set(ids)) != 10:
            raise SystemExit(f"{case['id']}: expected exactly 10 unique memory ids")
        relevant = list(case.get("relevant_memory_ids", []))
        if case["category"] == "ambiguous_no_evidence":
            if relevant:
                raise SystemExit(f"{case['id']}: no-evidence case unexpectedly has relevant ids")
            abstention += 1
        else:
            if len(relevant) != 1 or relevant[0] not in ids:
                raise SystemExit(f"{case['id']}: answerable case must have exactly one in-corpus relevant id")
            if len(memories) - len(relevant) != 9:
                raise SystemExit(f"{case['id']}: expected 9 distractors")
            answerable += 1
        if not isinstance(case.get("query"), str) or not case["query"].strip():
            raise SystemExit(f"{case['id']}: query missing")
        for memory in memories:
            if not isinstance(memory.get("text"), str) or not memory["text"].strip():
                raise SystemExit(f"{case['id']}: blank memory text")
            if not isinstance(memory.get("timestamp"), str) or not memory["timestamp"].strip():
                raise SystemExit(f"{case['id']}: timestamp missing")
        case_rows.append({
            "case_id": case["id"],
            "category": case["category"],
            "memory_count": len(memories),
            "relevant_count": len(relevant),
        })
    if answerable != 22 or abstention != 2:
        raise SystemExit(f"expected 22 answerable + 2 abstention, got {answerable}+{abstention}")

    manifest = {
        "schema_version": "pse-adversarial-v4-postfreeze-manifest-v1",
        "status": "FROZEN_BEFORE_ANY_V4_SYSTEM_EVALUATION",
        "corpus_path": args.corpus.as_posix(),
        "corpus_sha256": sha256_file(args.corpus),
        "corpus_bytes": args.corpus.stat().st_size,
        "source_commit": args.source_commit,
        "candidate_v2_freeze_commit": CANDIDATE_V2_FREEZE_COMMIT,
        "candidate_v2_source_commit": CANDIDATE_V2_SOURCE_COMMIT,
        "candidate_source_changed_for_v4": False,
        "case_count": 24,
        "answerable_case_count": 22,
        "abstention_case_count": 2,
        "categories": dict(sorted(categories.items())),
        "memory_count_per_case": 10,
        "distractors_per_answerable_case": 9,
        "operator_designed": True,
        "independent_reproduction": False,
        "sealed_final_accessed": False,
        "new_monetary_cost_usd": 0.0,
        "cases": case_rows,
        "claim_boundary": "Post-candidate-freeze benchmark-discrimination evidence; candidate source/config cannot be changed after observing v4 results without creating a new candidate version."
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ADVERSARIAL_V4_FROZEN", "corpus_sha256": manifest["corpus_sha256"], "cases": 24}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
