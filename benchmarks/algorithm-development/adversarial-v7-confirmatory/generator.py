from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_DATASET_SHA256 = "77f2113fdf67001c53a31f0d9eff4ecac7e71564335ab9a505665b44a05546cd"

RELATIONS = [
    ("balance", lambda i: str(7000 + i * 17)),
    ("date", lambda i: f"2026-09-{(i % 27) + 1:02d}"),
    ("preference", lambda i: f"mode-{i}"),
    ("approval", lambda i: f"Reviewer-{i}"),
    ("registration number", lambda i: f"REG-{9000 + i}"),
]


def memory(mid: str, text: str, day: int = 20) -> dict[str, Any]:
    return {"id": mid, "text": text, "timestamp": f"2026-08-{day:02d}T10:00:00+00:00"}


def case(cid: str, category: str, query: str, memories: list[dict[str, Any]], relevant: list[str]) -> dict[str, Any]:
    return {"id": cid, "category": category, "query": query, "memories": memories, "relevant_memory_ids": relevant}


def build_payload() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    # 60 answerable cases: fresh ADV7 namespace and five relations not used as the
    # primary relation set in Candidate-v6 protected validation.
    for block in range(12):
        for relation_index, (relation, value_factory) in enumerate(RELATIONS):
            n = block * 5 + relation_index + 1
            subject = f"ADV7-{n:03d}"
            value = value_factory(300 + n)
            query = f"What is the current {relation} for {subject}?"
            form = block % 4
            if form == 0:
                good = f"The current {relation} for {subject} is {value}."
            elif form == 1:
                good = f"{subject} current {relation} is {value}."
            elif form == 2:
                good = f"{subject}'s current {relation} is {value}."
            else:
                good = f"The {relation} for {subject} updated to {value}."
            memories = [
                memory("good", good, 20),
                memory("meta", f"Question about {subject} {relation} remains in the agenda only.", 22),
                memory("other", f"The current {relation} for ALT7-{n:03d} is DECOY-{n}.", 23),
                memory("noise", f"Unrelated logistics note number {n}.", 24),
            ]
            rotation = n % 4
            memories = memories[rotation:] + memories[:rotation]
            cases.append(case(f"adv7-a-{n:03d}", "answerable", query, memories, ["good"]))

    # 30 no-evidence/adversarial cases: six families x five cases.
    families = ["agenda_only", "review_topic", "explicit_no_value", "wrong_subject", "stale_only", "contradiction"]
    n = 61
    for family_index, family in enumerate(families):
        for offset in range(5):
            relation, value_factory = RELATIONS[(family_index + offset) % len(RELATIONS)]
            subject = f"ADV7-{n:03d}"
            value = value_factory(300 + n)
            query = f"What is the current {relation} for {subject}?"
            if family == "agenda_only":
                memories = [
                    memory("a", f"Question about {subject} {relation} remains in the agenda only.", 22),
                    memory("b", f"{subject} current {relation} agenda topic only.", 23),
                ]
            elif family == "review_topic":
                memories = [
                    memory("a", f"Review of the current {relation} for {subject} is a discussion topic only.", 22),
                    memory("b", f"{subject} current {relation} review topic only.", 23),
                ]
            elif family == "explicit_no_value":
                memories = [
                    memory("a", f"Review of the current {relation} for {subject} contains no recorded value.", 22),
                    memory("b", f"The {relation} question for {subject} has no known answer.", 23),
                ]
            elif family == "wrong_subject":
                memories = [
                    memory("a", f"The current {relation} for ALT7-{n:03d} is {value}.", 22),
                    memory("b", f"Question about {subject} {relation} remains open.", 23),
                ]
            elif family == "stale_only":
                memories = [
                    memory("a", f"The old {relation} for {subject} was {value}.", 5),
                    memory("b", f"Review of the current {relation} for {subject} remains pending.", 22),
                ]
            else:
                memories = [
                    memory("a", f"The current {relation} for {subject} is VALUE-A-{n}.", 22),
                    memory("b", f"The current {relation} for {subject} is VALUE-B-{n}.", 22),
                ]
            cases.append(case(f"adv7-n-{n:03d}", family, query, memories, []))
            n += 1

    if len(cases) != 90 or len({row["id"] for row in cases}) != 90:
        raise AssertionError("adversarial-v7 must contain exactly 90 unique cases")
    if sum(bool(row["relevant_memory_ids"]) for row in cases) != 60:
        raise AssertionError("adversarial-v7 answerable count mismatch")
    return {"schema_version": "adversarial-v7-confirmatory-cases-v1", "cases": cases}


def canonical_payload() -> str:
    return json.dumps(build_payload(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    payload = canonical_payload()
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if digest != EXPECTED_DATASET_SHA256:
        raise SystemExit(f"adversarial-v7 SHA mismatch: {digest} != {EXPECTED_DATASET_SHA256}")
    output = Path(__file__).with_name("cases-v1.json")
    output.write_text(payload, encoding="utf-8")
    print(json.dumps({"case_count": 90, "answerable_count": 60, "no_evidence_count": 30, "sha256": digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
