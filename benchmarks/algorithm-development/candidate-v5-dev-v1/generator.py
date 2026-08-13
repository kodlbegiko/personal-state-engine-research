from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

SEED = 20260813
RELATIONS = [
    "phone", "email", "budget", "balance", "price", "salary", "address", "location",
    "date", "time", "color", "status", "owner", "code", "pin", "serial_number",
    "version", "provider", "preference",
]
VALUES = {
    "phone": ["+1-555-0101", "+1-555-0102", "+1-555-0103", "+1-555-0104"],
    "email": ["alpha@example.test", "beta@example.test", "gamma@example.test", "delta@example.test"],
    "budget": ["4800", "5200", "6100", "7300"],
    "balance": ["1250", "2140", "3050", "4180"],
    "price": ["89", "129", "159", "199"],
    "salary": ["42000", "48000", "53000", "61000"],
    "address": ["17-Oak-Street", "24-Pine-Road", "8-Lake-Avenue", "33-Hill-Lane"],
    "location": ["Room-301", "Shelf-B7", "Site-East", "Cabinet-4"],
    "date": ["2026-09-11", "2026-09-18", "2026-10-02", "2026-10-09"],
    "time": ["09:30", "11:00", "14:30", "16:00"],
    "color": ["amber", "cobalt", "ivory", "teal"],
    "status": ["active", "paused", "approved", "closed"],
    "owner": ["Mira", "Jonas", "Kei", "Lena"],
    "code": ["ZX-41", "QP-77", "LM-20", "TR-58"],
    "pin": ["4812", "7329", "1504", "9961"],
    "serial_number": ["SN-A14", "SN-B27", "SN-C39", "SN-D52"],
    "version": ["v2.4", "v3.1", "v4.0", "v5.2"],
    "provider": ["Northwind", "BluePeak", "Redwood", "Solace"],
    "preference": ["window-seat", "dark-mode", "tea", "morning-slot"],
}
ANSWERABLE_FAMILIES = [
    "single_support", "multi_support", "temporal_update", "duplicate_distractor",
    "stale_distractor_with_fresh_evidence", "paraphrased_query", "multi_session_evidence",
    "contradiction_resolved", "lexical_distractor", "noisy_context",
]
NO_EVIDENCE_FAMILIES = [
    "wrong_subject", "wrong_predicate", "wrong_value", "missing_slot", "partial_evidence",
    "stale_only", "contradictory_unresolved", "unsupported_inference", "query_echo",
    "near_duplicate", "temporal_near_match", "high_lexical_overlap",
]


def _ts(day: int) -> str:
    return f"2026-08-{day:02d}T10:00:00+00:00"


def _m(mid: str, text: str, day: int = 7) -> dict:
    return {"id": mid, "text": text, "timestamp": _ts(day)}


def _rel(index: int) -> str:
    return RELATIONS[index % len(RELATIONS)]


def _value(relation: str, variant: int) -> str:
    return VALUES[relation][variant % 4]


def _label(relation: str) -> str:
    return relation.replace("_", " ")


def build_cases() -> list[dict]:
    cases: list[dict] = []
    cid = 1

    for family in ANSWERABLE_FAMILIES:
        for variant in range(4):
            subject = f"Entity-{cid + 1:03d}"
            relation = _rel(cid + variant)
            value = _value(relation, variant)
            label = _label(relation)
            query = f"What is the current {label} for {subject}?"
            relevant: list[str] = []

            if family == "single_support":
                memories = [
                    _m(f"{cid}-a", f"The current {label} for {subject} is {value}."),
                    _m(f"{cid}-b", query, 8),
                    _m(f"{cid}-c", f"The current {label} for Other-{cid:03d} is {_value(relation, variant + 1)}.", 8),
                ]
                relevant = [f"{cid}-a"]
            elif family == "multi_support":
                relation2 = _rel(RELATIONS.index(relation) + 1)
                value2 = _value(relation2, variant)
                query = f"What are the current {label} and {_label(relation2)} for {subject}?"
                memories = [
                    _m(f"{cid}-a", f"The current {label} for {subject} is {value}."),
                    _m(f"{cid}-b", f"The current {_label(relation2)} for {subject} is {value2}."),
                    _m(f"{cid}-c", f"The {label} for Other-{cid:03d} is {_value(relation, variant + 1)}.", 8),
                ]
                relevant = [f"{cid}-a", f"{cid}-b"]
            elif family == "temporal_update":
                old = _value(relation, variant + 1)
                memories = [
                    _m(f"{cid}-a", f"The old {label} for {subject} was {old}.", 2),
                    _m(f"{cid}-b", f"The {label} for {subject} was updated to {value}; this is current."),
                    _m(f"{cid}-c", f"The current {label} for Other-{cid:03d} is {old}.", 8),
                ]
                relevant = [f"{cid}-b"]
            elif family == "duplicate_distractor":
                memories = [
                    _m(f"{cid}-a", f"The current {label} for {subject} is {value}."),
                    _m(f"{cid}-b", f"Current {label} for {subject}: {value}."),
                    _m(f"{cid}-c", query, 8),
                ]
                relevant = [f"{cid}-a", f"{cid}-b"]
            elif family == "stale_distractor_with_fresh_evidence":
                old = _value(relation, variant + 2)
                memories = [
                    _m(f"{cid}-a", f"The previous stale {label} for {subject} was {old}.", 1),
                    _m(f"{cid}-b", f"The current {label} for {subject} is {value}."),
                    _m(f"{cid}-c", f"Archive note about {subject} {label}.", 3),
                ]
                relevant = [f"{cid}-b"]
            elif family == "paraphrased_query":
                query = f"Which {label} is currently recorded for {subject}?"
                memories = [
                    _m(f"{cid}-a", f"For {subject}, the current {label} is {value}."),
                    _m(f"{cid}-b", query, 8),
                    _m(f"{cid}-c", f"For Other-{cid:03d}, the {label} is {_value(relation, variant + 1)}.", 8),
                ]
                relevant = [f"{cid}-a"]
            elif family == "multi_session_evidence":
                memories = [
                    _m(f"{cid}-a", f"Session one: {subject} uses {label} {value}.", 5),
                    _m(f"{cid}-b", f"Session two discussed unrelated shipping for {subject}.", 7),
                    _m(f"{cid}-c", f"The current {label} for Other-{cid:03d} is {_value(relation, variant + 1)}.", 8),
                ]
                relevant = [f"{cid}-a"]
            elif family == "contradiction_resolved":
                old = _value(relation, variant + 1)
                memories = [
                    _m(f"{cid}-a", f"The old {label} for {subject} was {old}.", 2),
                    _m(f"{cid}-b", f"Correction: {subject} {label} changed to {value}; this replaces the old value."),
                    _m(f"{cid}-c", f"Historical note: {subject} {label} was {old}.", 2),
                ]
                relevant = [f"{cid}-b"]
            elif family == "lexical_distractor":
                memories = [
                    _m(f"{cid}-a", f"The current {label} for {subject} is {value}."),
                    _m(f"{cid}-b", f"{subject} {label} current current {label} question discussion.", 8),
                    _m(f"{cid}-c", f"Other-{cid:03d} has {label} {_value(relation, variant + 1)}.", 8),
                ]
                relevant = [f"{cid}-a"]
            else:
                memories = [
                    _m(f"{cid}-a", f"Meeting notes, unrelated logistics, and then a confirmed fact: the current {label} for {subject} is {value}."),
                    _m(f"{cid}-b", f"Unrelated notes mention {subject} and scheduling only.", 8),
                    _m(f"{cid}-c", f"The {label} for Other-{cid:03d} is {_value(relation, variant + 1)}.", 8),
                ]
                relevant = [f"{cid}-a"]

            cases.append({"id": f"dev-a-{cid:03d}", "category": family, "query": query, "memories": memories, "relevant_memory_ids": relevant})
            cid += 1

    for family in NO_EVIDENCE_FAMILIES:
        for variant in range(4):
            subject = f"Entity-{cid + 1:03d}"
            relation = _rel(cid + variant)
            value = _value(relation, variant)
            label = _label(relation)
            query = f"What is the current {label} for {subject}?"

            if family == "wrong_subject":
                memories = [
                    _m(f"{cid}-a", f"The current {label} for Other-{cid:03d} is {value}."),
                    _m(f"{cid}-b", f"{subject} is mentioned in this note but no {label} is given.", 8),
                ]
            elif family == "wrong_predicate":
                relation2 = _rel(RELATIONS.index(relation) + 1)
                memories = [
                    _m(f"{cid}-a", f"The current {_label(relation2)} for {subject} is {_value(relation2, variant)}."),
                    _m(f"{cid}-b", f"{subject} {label} is discussed without a value.", 8),
                ]
            elif family == "wrong_value":
                memories = [
                    _m(f"{cid}-a", f"The value {value} is a wrong {label} for {subject}; do not use it."),
                    _m(f"{cid}-b", f"No confirmed {label} for {subject} is available.", 8),
                ]
            elif family in {"missing_slot", "partial_evidence"}:
                relation2 = _rel(RELATIONS.index(relation) + 1)
                query = f"What are the current {label} and {_label(relation2)} for {subject}?"
                if family == "missing_slot":
                    second = f"{subject} has no recorded {_label(relation2)}."
                else:
                    second = f"The {_label(relation2)} question for {subject} remains unresolved."
                memories = [
                    _m(f"{cid}-a", f"The current {label} for {subject} is {value}."),
                    _m(f"{cid}-b", second, 8),
                ]
            elif family == "stale_only":
                memories = [
                    _m(f"{cid}-a", f"The old stale {label} for {subject} was {value}.", 2),
                    _m(f"{cid}-b", f"Historical archive: {subject} previously used {label} {value}.", 1),
                ]
            elif family == "contradictory_unresolved":
                memories = [
                    _m(f"{cid}-a", f"The {label} for {subject} is {value}.", 6),
                    _m(f"{cid}-b", f"The {label} for {subject} is {_value(relation, variant + 1)}.", 6),
                ]
            elif family == "unsupported_inference":
                memories = [
                    _m(f"{cid}-a", f"Because {subject} uses a related service, the {label} is probably {value}."),
                    _m(f"{cid}-b", f"No direct {label} record exists for {subject}.", 8),
                ]
            elif family == "query_echo":
                memories = [_m(f"{cid}-a", query, 8), _m(f"{cid}-b", f"Question repeated: {query}", 8)]
            elif family == "near_duplicate":
                memories = [
                    _m(f"{cid}-a", f"Please record the question: what is the current {label} for {subject}; answer not present.", 8),
                    _m(f"{cid}-b", f"{subject} current {label} remains unknown.", 8),
                ]
            elif family == "temporal_near_match":
                memories = [
                    _m(f"{cid}-a", f"Before the current period, the {label} for {subject} was {value}.", 2),
                    _m(f"{cid}-b", f"A prior note about {subject} lists {label} {value}.", 3),
                ]
            else:
                memories = [
                    _m(f"{cid}-a", f"{subject} current {label} current {subject} {label} query topic only.", 8),
                    _m(f"{cid}-b", f"Discussion of the current {label} for {subject} contains no recorded value.", 8),
                ]

            cases.append({"id": f"dev-n-{cid:03d}", "category": family, "query": query, "memories": memories, "relevant_memory_ids": []})
            cid += 1

    return cases


def canonical_jsonl(cases: list[dict] | None = None) -> str:
    rows = cases if cases is not None else build_cases()
    return "\n".join(json.dumps(case, ensure_ascii=False, sort_keys=True) for case in rows) + "\n"


def dataset_sha256(cases: list[dict] | None = None) -> str:
    return hashlib.sha256(canonical_jsonl(cases).encode("utf-8")).hexdigest()


def manifest() -> dict:
    cases = build_cases()
    counts = Counter(case["category"] for case in cases)
    return {
        "schema_version": "candidate-v5-dev-manifest-v1",
        "seed": SEED,
        "case_count": len(cases),
        "answerable_count": sum(bool(case["relevant_memory_ids"]) for case in cases),
        "no_evidence_count": sum(not bool(case["relevant_memory_ids"]) for case in cases),
        "family_counts": dict(sorted(counts.items())),
        "dataset_sha256": dataset_sha256(cases),
        "v6_cases_copied": False,
        "sealed_final_accessed": False,
        "monetary_cost_usd": 0,
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    (root / "cases.jsonl").write_text(canonical_jsonl(), encoding="utf-8")
    (root / "manifest.generated.json").write_text(json.dumps(manifest(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest(), indent=2, sort_keys=True))
