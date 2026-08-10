#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC = ROOT / "benchmarks/algorithm-development/adversarial-v5/case-specifications-v1.json"


def m(mid: str, text: str, day: int) -> dict:
    return {"id": mid, "text": text, "timestamp": f"2026-07-{day:02d}"}


def materialize(spec: dict) -> dict:
    rng = random.Random(spec["generation_seed"])
    cases = []

    def add_answerable(i: int, row: dict) -> None:
        rels = row["relevant"]
        memories = []
        rel_ids = []
        for j, text in enumerate(rels, 1):
            rel_ids.append(f"r{j}")
            memories.append(m(f"r{j}", text, max(1, (i + j) % 27 + 1)))
        hard = row["hard_distractor"]
        extras = [hard, hard] if row["category"] == "duplicate_distractor" else []
        base = [
            hard,
            row["query"].rstrip("?？") + " answer reference note.",
            "A recent administrative note discusses the same project but not the requested fact.",
            "An older document contains nearby terminology but a different attribute.",
            "The related checklist was reviewed this month.",
            "A different entity has a superficially similar value.",
            "The topic appears in a glossary without stating the requested answer.",
        ]
        distractors = (extras + base)[: 8 - len(rels)]
        for j, text in enumerate(distractors, 1):
            memories.append(m(f"d{j}", text, max(1, (i * 3 + j) % 27 + 1)))
        rng.shuffle(memories)
        cases.append({
            "id": f"ADV5-C-{i:03d}",
            "category": row["category"],
            "memories": memories,
            "query": row["query"],
            "relevant_memory_ids": rel_ids,
        })

    def add_no_evidence(i: int, row: dict) -> None:
        hard = row["hard_distractor"]
        extras = []
        if row["category"] == "duplicate_distractor_no_answer":
            extras = [hard, hard]
        elif row["category"] == "conflict_no_resolution":
            extras = [
                "The workshop may be in Room B.",
                "A draft agenda says Room A.",
                "A second draft says Room B.",
            ]
        base = [
            hard,
            row["query"].rstrip("?？") + " answer query note.",
            "A recent note discusses the same entity but a different field.",
            "An old document uses similar wording without asserting the requested fact.",
            "A different entity has a plausible-looking value.",
            "The related policy was reviewed this month.",
            "A glossary lists the requested term but no answer.",
            "A status update mentions the topic only.",
        ]
        distractors = (extras + base)[:8]
        memories = [
            m(f"d{j}", text, max(1, (i * 3 + j) % 27 + 1))
            for j, text in enumerate(distractors, 1)
        ]
        rng.shuffle(memories)
        cases.append({
            "id": f"ADV5-C-{i:03d}",
            "category": row["category"],
            "memories": memories,
            "query": row["query"],
            "relevant_memory_ids": [],
        })

    i = 1
    for row in spec["answerable"]:
        add_answerable(i, row)
        i += 1
    for row in spec["no_evidence"]:
        add_no_evidence(i, row)
        i += 1

    category_counts = {}
    for case in cases:
        category_counts[case["category"]] = category_counts.get(case["category"], 0) + 1

    return {
        "schema_version": "pse-adversarial-v5-confirmatory-v1",
        "generation_note": "New non-sealed confirmatory benchmark created only after candidate-v3 was frozen and passed one-time validation. Cases are synthetic, mechanism-agnostic, and include unseen relations/paraphrases, temporal conflicts, lexical/query-echo distractors, duplicate clusters, stale/recency traps, multiple-relevant cases, and hard no-evidence cases. No system was executed on v5 before this corpus was frozen.",
        "design": {
            "case_count": len(cases),
            "answerable_case_count": sum(bool(c["relevant_memory_ids"]) for c in cases),
            "abstention_case_count": sum(not c["relevant_memory_ids"] for c in cases),
            "category_counts": category_counts,
            "memory_count_per_case": 8,
            "generation_seed": spec["generation_seed"],
            "candidate_tuning_after_generation": False,
            "mechanism_agnostic_design": True,
            "includes_unseen_relations_and_paraphrases": True,
            "sealed_final_accessed": False,
        },
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    payload = materialize(spec)
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
