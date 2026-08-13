from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SEED = 20260813
EXPECTED_DATASET_SHA256 = "855f812b3eec93f3229fe804ebd20e6e86baee5f99e9b322d11c114821215dc7"

RELATIONS = [
    ("serial number", lambda i: f"SN-{2026+i:05d}"),
    ("owner", lambda i: f"Owner-{i}"),
    ("timezone", lambda i: f"UTC+{(i%12)+1:02d}:00"),
    ("address", lambda i: f"{100+i} Cedar Lane"),
    ("salary", lambda i: str(60000 + i*125)),
    ("price", lambda i: f"${100+i}.50"),
    ("pin", lambda i: f"{1000+i}"),
    ("expiry", lambda i: f"2027-{(i%12)+1:02d}-{(i%27)+1:02d}"),
    ("quantity", lambda i: str(20+i)),
    ("type", lambda i: f"TYPE-{chr(65+(i%26))}{i}"),
]


def _memory(mid: str, text: str, day: int = 15) -> dict[str, Any]:
    return {"id": mid, "text": text, "timestamp": f"2026-08-{day:02d}T10:00:00+00:00"}


def _case(cid: str, category: str, query: str, memories: list[dict[str, Any]], relevant: list[str], verdict: str) -> dict[str, Any]:
    return {
        "id": cid,
        "category": category,
        "query": query,
        "memories": memories,
        "relevant_memory_ids": relevant,
        "expected_candidate_v6_verdict": verdict,
    }


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    # 40 answerable cases over relations not used by the Candidate-v6 development generator.
    for block in range(4):
        for relation_index, (relation, value_factory) in enumerate(RELATIONS):
            n = block * 10 + relation_index + 1
            subject = f"PVX-{n:03d}"
            value = value_factory(200 + n)
            query = f"What is the current {relation} for {subject}?"
            if block == 0:
                good = f"The current {relation} for {subject} is {value}."
                memories = [
                    _memory("a", good, 15),
                    _memory("b", f"Question about {subject} {relation} remains in the agenda only.", 16),
                    _memory("c", f"The current {relation} for ALT-{n:03d} is DECOY-{n}.", 17),
                ]
            elif block == 1:
                good = f"{subject} current {relation} is {value}."
                memories = [
                    _memory("a", good, 16),
                    _memory("b", f"Review of the current {relation} for {subject} is a topic only.", 17),
                ]
            elif block == 2:
                good = f"{subject}'s current {relation} is {value}."
                memories = [
                    _memory("a", good, 16),
                    _memory("b", f"The old {relation} for {subject} was LEGACY-{n}.", 5),
                    _memory("c", f"Discussion about {subject} {relation} mentions terminology only.", 17),
                ]
            else:
                good = f"The {relation} for {subject} changed to {value}."
                memories = [
                    _memory("a", good, 18),
                    _memory("b", f"The old {relation} for {subject} was LEGACY-{n}.", 5),
                    _memory("c", f"Question about {subject} {relation} remains open.", 17),
                ]
            cases.append(_case(f"pv-a-{n:03d}", "answerable_fresh_relation", query, memories, ["a"], "SUPPORTED"))

    # 40 no-evidence/adversarial cases: eight families, five cases each.
    families = [
        "agenda_only", "explicit_no_value", "wrong_subject", "wrong_relation",
        "stale_only", "contradiction", "unsupported_inference", "review_topic",
    ]
    n = 41
    for family_index, family in enumerate(families):
        for offset in range(5):
            relation, value_factory = RELATIONS[(family_index * 3 + offset) % len(RELATIONS)]
            subject = f"PVX-{n:03d}"
            query = f"What is the current {relation} for {subject}?"
            value = value_factory(200 + n)
            if family == "agenda_only":
                memories = [
                    _memory("a", f"Question about {subject} {relation} remains in the agenda only.", 16),
                    _memory("b", f"{subject} current {relation} review topic only.", 17),
                ]
                verdict = "INSUFFICIENT"
            elif family == "explicit_no_value":
                memories = [
                    _memory("a", f"Review of the current {relation} for {subject} contains no recorded value.", 16),
                    _memory("b", f"The {relation} question for {subject} has no known answer.", 17),
                ]
                verdict = "INSUFFICIENT"
            elif family == "wrong_subject":
                memories = [
                    _memory("a", f"The current {relation} for ALT-{n:03d} is {value}.", 16),
                    _memory("b", f"Question about {subject} {relation} remains open.", 17),
                ]
                verdict = "INSUFFICIENT"
            elif family == "wrong_relation":
                other_relation = RELATIONS[((family_index * 3 + offset) + 1) % len(RELATIONS)][0]
                memories = [
                    _memory("a", f"The current {other_relation} for {subject} is DECOY-{n}.", 16),
                    _memory("b", f"Question about {subject} {relation} remains open.", 17),
                ]
                verdict = "INSUFFICIENT"
            elif family == "stale_only":
                memories = [
                    _memory("a", f"The old {relation} for {subject} was {value}.", 5),
                    _memory("b", f"Review of the current {relation} for {subject} remains pending.", 16),
                ]
                verdict = "INSUFFICIENT"
            elif family == "contradiction":
                memories = [
                    _memory("a", f"The current {relation} for {subject} is VALUE-A-{n}.", 16),
                    _memory("b", f"The current {relation} for {subject} is VALUE-B-{n}.", 16),
                ]
                verdict = "CONTRADICTED"
            elif family == "unsupported_inference":
                memories = [
                    _memory("a", f"The current {relation} for {subject} is probably {value}.", 16),
                    _memory("b", f"Review notes for {subject} {relation} are incomplete.", 17),
                ]
                verdict = "INSUFFICIENT"
            else:
                memories = [
                    _memory("a", f"Review of the current {relation} for {subject} is a discussion topic only.", 16),
                    _memory("b", f"{subject} current {relation} review topic only.", 17),
                ]
                verdict = "INSUFFICIENT"
            cases.append(_case(f"pv-n-{n:03d}", family, query, memories, [], verdict))
            n += 1

    if len(cases) != 80:
        raise AssertionError(f"unexpected case count: {len(cases)}")
    if sum(bool(case["relevant_memory_ids"]) for case in cases) != 40:
        raise AssertionError("unexpected answerable count")
    return cases


def canonical_jsonl(cases: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n" for case in cases)


def dataset_sha256(cases: list[dict[str, Any]]) -> str:
    return hashlib.sha256(canonical_jsonl(cases).encode("utf-8")).hexdigest()


def main() -> int:
    cases = build_cases()
    payload = canonical_jsonl(cases)
    digest = dataset_sha256(cases)
    if digest != EXPECTED_DATASET_SHA256:
        raise SystemExit(f"dataset SHA mismatch: {digest} != {EXPECTED_DATASET_SHA256}")
    output = Path(__file__).with_name("cases.jsonl")
    output.write_text(payload, encoding="utf-8")
    print(json.dumps({
        "seed": SEED,
        "case_count": len(cases),
        "answerable_count": sum(bool(case["relevant_memory_ids"]) for case in cases),
        "no_evidence_count": sum(not bool(case["relevant_memory_ids"]) for case in cases),
        "sha256": digest,
        "output": str(output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
