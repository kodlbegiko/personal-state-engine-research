from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

SEED = 20260813

RELATIONS = [
    ("email", ["iris@validation.test", "jade@validation.test"]),
    ("phone", ["+44-20-7000-1101", "+44-20-7000-1102"]),
    ("budget", ["8450", "9175"]),
    ("status", ["ready", "paused"]),
    ("color", ["saffron", "indigo"]),
    ("owner", ["Nora", "Pavel"]),
    ("code", ["VX-804", "KQ-219"]),
    ("version", ["v7.3", "v8.1"]),
    ("provider", ["AsterWorks", "CedarGrid"]),
    ("location", ["Bay-12", "Zone-Delta"]),
    ("date", ["2026-10-14", "2026-10-21"]),
    ("time", ["10:45", "15:20"]),
]

ANSWERABLE_FAMILIES = [
    "direct_assertion",
    "split_multi_requirement",
    "fresh_supersedes_stale",
    "resolved_revision",
    "paraphrased_prompt",
    "wrong_subject_distractor",
    "wrong_relation_distractor",
    "consistent_duplicate",
    "cross_session_support",
    "lexical_noise",
    "fresh_plus_archive",
    "concise_fact",
]

NO_EVIDENCE_FAMILIES = [
    "wrong_subject",
    "wrong_relation",
    "invalidated_value",
    "missing_required_slot",
    "stale_only",
    "unresolved_conflict",
    "inference_only",
    "echo_only",
    "near_duplicate_no_answer",
    "temporal_before_only",
    "high_overlap_no_value",
    "ambiguous_multi_entity",
]


def _m(mid: str, text: str, day: int) -> dict:
    return {"id": mid, "text": text, "timestamp": f"2026-08-{day:02d}T09:15:00+00:00"}


def _rel(index: int) -> tuple[str, list[str]]:
    return RELATIONS[index % len(RELATIONS)]


def build_cases() -> list[dict]:
    cases: list[dict] = []
    serial = 1

    for family_index, family in enumerate(ANSWERABLE_FAMILIES):
        for variant in range(2):
            relation, values = _rel(family_index + variant)
            value = values[variant]
            other_value = values[1 - variant]
            subject = f"VAL-{serial:03d}"
            other_subject = f"ALT-{serial:03d}"
            q = f"Which current {relation} is recorded for {subject}?"
            relevant: list[str] = []

            if family == "direct_assertion":
                memories = [
                    _m(f"{serial}-a", f"For {subject}, the current {relation} is {value}.", 11),
                    _m(f"{serial}-b", f"For {other_subject}, the current {relation} is {other_value}.", 12),
                    _m(f"{serial}-c", f"Current {relation} review for {subject} has no recorded value.", 12),
                ]
                relevant = [f"{serial}-a"]
            elif family == "split_multi_requirement":
                relation2, values2 = _rel(family_index + variant + 3)
                value2 = values2[variant]
                q = f"What are the current {relation} and {relation2} for {subject}?"
                memories = [
                    _m(f"{serial}-a", f"The current {relation} for {subject} is {value}.", 10),
                    _m(f"{serial}-b", f"The current {relation2} for {subject} is {value2}.", 11),
                    _m(f"{serial}-c", f"The {relation} for {other_subject} is {other_value}.", 12),
                ]
                relevant = [f"{serial}-a", f"{serial}-b"]
            elif family == "fresh_supersedes_stale":
                memories = [
                    _m(f"{serial}-a", f"Historical stale {relation} for {subject} was {other_value}.", 2),
                    _m(f"{serial}-b", f"The {relation} for {subject} was updated to {value}; this is the current record.", 11),
                    _m(f"{serial}-c", f"Archive note for {other_subject}: {relation} {other_value}.", 3),
                ]
                relevant = [f"{serial}-b"]
            elif family == "resolved_revision":
                memories = [
                    _m(f"{serial}-a", f"The old {relation} for {subject} was {other_value}.", 3),
                    _m(f"{serial}-b", f"Correction: {subject} {relation} changed to {value}; this replaces the old value.", 12),
                    _m(f"{serial}-c", f"Old notes for {other_subject} list {relation} {other_value}.", 4),
                ]
                relevant = [f"{serial}-b"]
            elif family == "paraphrased_prompt":
                q = f"What is the current {relation} for {subject}?"
                memories = [
                    _m(f"{serial}-a", f"Confirmed fact for {subject}: current {relation} is {value}.", 11),
                    _m(f"{serial}-b", f"A meeting asks about the current {relation} for {subject} but records no answer.", 12),
                    _m(f"{serial}-c", f"{other_subject} has {relation} {other_value}.", 12),
                ]
                relevant = [f"{serial}-a"]
            elif family == "wrong_subject_distractor":
                memories = [
                    _m(f"{serial}-a", f"The current {relation} for {other_subject} is {other_value}.", 12),
                    _m(f"{serial}-b", f"For {subject}, the current {relation} is {value}.", 10),
                    _m(f"{serial}-c", f"{subject} appears in unrelated logistics notes.", 12),
                ]
                relevant = [f"{serial}-b"]
            elif family == "wrong_relation_distractor":
                relation2, values2 = _rel(family_index + variant + 2)
                memories = [
                    _m(f"{serial}-a", f"The current {relation2} for {subject} is {values2[variant]}.", 12),
                    _m(f"{serial}-b", f"The current {relation} for {subject} is {value}.", 10),
                    _m(f"{serial}-c", f"Question about {subject} {relation} remains in the agenda only.", 12),
                ]
                relevant = [f"{serial}-b"]
            elif family == "consistent_duplicate":
                memories = [
                    _m(f"{serial}-a", f"The current {relation} for {subject} is {value}.", 10),
                    _m(f"{serial}-b", f"Confirmed current {relation} for {subject}: {value}.", 11),
                    _m(f"{serial}-c", f"{other_subject} current {relation} is {other_value}.", 12),
                ]
                relevant = [f"{serial}-a", f"{serial}-b"]
            elif family == "cross_session_support":
                relation2, values2 = _rel(family_index + variant + 2)
                value2 = values2[variant]
                q = f"What are the current {relation} and {relation2} for {subject}?"
                memories = [
                    _m(f"{serial}-a", f"Session A records the current {relation} for {subject} as {value}.", 9),
                    _m(f"{serial}-b", f"Session B records the current {relation2} for {subject} as {value2}.", 11),
                    _m(f"{serial}-c", f"Session C contains unrelated notes for {subject}.", 12),
                ]
                relevant = [f"{serial}-a", f"{serial}-b"]
            elif family == "lexical_noise":
                memories = [
                    _m(f"{serial}-a", f"Agenda: current {relation}, {subject}, review, current, review, no value recorded.", 12),
                    _m(f"{serial}-b", f"Final confirmed fact: the current {relation} for {subject} is {value}.", 10),
                    _m(f"{serial}-c", f"Current current {relation} {other_subject} {relation} topic.", 12),
                ]
                relevant = [f"{serial}-b"]
            elif family == "fresh_plus_archive":
                memories = [
                    _m(f"{serial}-a", f"Archive: the previous {relation} for {subject} was {other_value}.", 1),
                    _m(f"{serial}-b", f"The current {relation} for {subject} is {value}.", 12),
                    _m(f"{serial}-c", f"Historical discussion of {subject} contains no current value.", 2),
                ]
                relevant = [f"{serial}-b"]
            else:
                memories = [
                    _m(f"{serial}-a", f"{subject}: current {relation} = {value}.", 11),
                    _m(f"{serial}-b", f"{other_subject}: current {relation} = {other_value}.", 12),
                ]
                relevant = [f"{serial}-a"]

            cases.append({
                "id": f"validation-a-{serial:03d}",
                "category": family,
                "query": q,
                "memories": memories,
                "relevant_memory_ids": relevant,
            })
            serial += 1

    for family_index, family in enumerate(NO_EVIDENCE_FAMILIES):
        for variant in range(2):
            relation, values = _rel(family_index + variant + 1)
            value = values[variant]
            other_value = values[1 - variant]
            subject = f"VAL-{serial:03d}"
            other_subject = f"ALT-{serial:03d}"
            q = f"What is the current {relation} for {subject}?"

            if family == "wrong_subject":
                memories = [
                    _m(f"{serial}-a", f"The current {relation} for {other_subject} is {value}.", 12),
                    _m(f"{serial}-b", f"{subject} appears in a general note without any {relation} value.", 11),
                ]
            elif family == "wrong_relation":
                relation2, values2 = _rel(family_index + variant + 4)
                memories = [
                    _m(f"{serial}-a", f"The current {relation2} for {subject} is {values2[variant]}.", 12),
                    _m(f"{serial}-b", f"The {relation} topic for {subject} is open but no answer is recorded.", 11),
                ]
            elif family == "invalidated_value":
                memories = [
                    _m(f"{serial}-a", f"{value} is an incorrect {relation} for {subject}; do not use it.", 11),
                    _m(f"{serial}-b", f"No confirmed {relation} exists for {subject}.", 12),
                ]
            elif family == "missing_required_slot":
                relation2, _ = _rel(family_index + variant + 5)
                q = f"What are the current {relation} and {relation2} for {subject}?"
                memories = [
                    _m(f"{serial}-a", f"The current {relation} for {subject} is {value}.", 11),
                    _m(f"{serial}-b", f"The {relation2} for {subject} is unresolved.", 12),
                ]
            elif family == "stale_only":
                memories = [
                    _m(f"{serial}-a", f"The old stale {relation} for {subject} was {value}.", 2),
                    _m(f"{serial}-b", f"Archive record: {subject} previously used {relation} {other_value}.", 3),
                ]
            elif family == "unresolved_conflict":
                memories = [
                    _m(f"{serial}-a", f"The {relation} for {subject} is {value}.", 10),
                    _m(f"{serial}-b", f"The {relation} for {subject} is {other_value}.", 10),
                ]
            elif family == "inference_only":
                memories = [
                    _m(f"{serial}-a", f"Based on an adjacent fact, the {relation} for {subject} is probably {value}.", 11),
                    _m(f"{serial}-b", f"No direct {relation} record exists for {subject}.", 12),
                ]
            elif family == "echo_only":
                memories = [
                    _m(f"{serial}-a", q, 12),
                    _m(f"{serial}-b", f"Restated question: {q}", 12),
                ]
            elif family == "near_duplicate_no_answer":
                memories = [
                    _m(f"{serial}-a", f"Please record this query about the current {relation} for {subject}; answer not present.", 12),
                    _m(f"{serial}-b", f"The current {relation} for {subject} remains unknown.", 12),
                ]
            elif family == "temporal_before_only":
                memories = [
                    _m(f"{serial}-a", f"Before the current period, the {relation} for {subject} was {value}.", 3),
                    _m(f"{serial}-b", f"A prior historical note lists {subject} {relation} {other_value}.", 2),
                ]
            elif family == "high_overlap_no_value":
                memories = [
                    _m(f"{serial}-a", f"{subject} current {relation} current {subject} {relation} review topic only.", 12),
                    _m(f"{serial}-b", f"Review of the current {relation} for {subject} contains no recorded value.", 12),
                ]
            else:
                memories = [
                    _m(f"{serial}-a", f"The current {relation} for {subject} or {other_subject} is {value}; ownership is unresolved.", 12),
                    _m(f"{serial}-b", f"No uniquely assigned {relation} is recorded for {subject}.", 12),
                ]

            cases.append({
                "id": f"validation-n-{serial:03d}",
                "category": family,
                "query": q,
                "memories": memories,
                "relevant_memory_ids": [],
            })
            serial += 1

    return cases


def canonical_jsonl(cases: list[dict] | None = None) -> str:
    rows = build_cases() if cases is None else cases
    return "\n".join(json.dumps(case, ensure_ascii=False, sort_keys=True) for case in rows) + "\n"


def dataset_sha256(cases: list[dict] | None = None) -> str:
    return hashlib.sha256(canonical_jsonl(cases).encode("utf-8")).hexdigest()


def manifest() -> dict:
    cases = build_cases()
    counts = Counter(case["category"] for case in cases)
    return {
        "schema_version": "candidate-v5-protected-validation-manifest-v1",
        "created_after_candidate_v5_freeze": True,
        "seed": SEED,
        "case_count": len(cases),
        "answerable_count": sum(bool(case["relevant_memory_ids"]) for case in cases),
        "no_evidence_count": sum(not bool(case["relevant_memory_ids"]) for case in cases),
        "family_counts": dict(sorted(counts.items())),
        "dataset_sha256": dataset_sha256(cases),
        "reuses_candidate_v5_dev_cases": False,
        "reuses_adversarial_v6_cases": False,
        "new_entities": True,
        "new_paraphrases": True,
        "new_temporal_constructions": True,
        "new_distractor_combinations": True,
        "one_formal_execution_only": True,
        "sealed_final_accessed": False,
        "monetary_cost_usd": 0,
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    (root / "cases.jsonl").write_text(canonical_jsonl(), encoding="utf-8")
    (root / "manifest.generated.json").write_text(json.dumps(manifest(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest(), indent=2, sort_keys=True))
