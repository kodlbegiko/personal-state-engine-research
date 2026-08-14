from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SEED = 20260813
EXPECTED_DATASET_SHA256 = "393f669de845a4e3443273217d880d584035135643eaa933f6096b088b4cc25d"

RELATIONS = [
    ("code", lambda i: f"VX-{800 + i}"),
    ("version", lambda i: f"v{(i % 9) + 1}-{i}"),
    ("provider", lambda i: f"Provider-{i}"),
    ("email", lambda i: f"user{i}@example.test"),
    ("phone", lambda i: f"+1-555-{1000 + i}"),
    ("budget", lambda i: str(5000 + i * 10)),
    ("status", lambda i: f"STATE-{i}"),
    ("color", lambda i: f"color-{i}"),
    ("time", lambda i: f"{(8 + i) % 24:02d}:30"),
    ("location", lambda i: f"Room-{i}"),
]


def _memory(mid: str, text: str, day: int = 10) -> dict[str, Any]:
    return {"id": mid, "text": text, "timestamp": f"2026-08-{day:02d}T10:00:00+00:00"}


def _case(
    cid: str,
    category: str,
    query: str,
    memories: list[dict[str, Any]],
    relevant: list[str],
    diagnostic_targets: list[dict[str, str]] | None = None,
    verdict: str | None = None,
) -> dict[str, Any]:
    return {
        "id": cid,
        "category": category,
        "query": query,
        "memories": memories,
        "relevant_memory_ids": relevant,
        "diagnostic_targets": diagnostic_targets or [],
        "expected_candidate_v6_verdict": verdict or ("SUPPORTED" if relevant else "INSUFFICIENT"),
    }


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    # 50 answerable cases: five assertion/temporal constructions across ten relations.
    for block in range(5):
        for relation_index, (relation, value_factory) in enumerate(RELATIONS):
            n = block * 10 + relation_index + 1
            subject = f"DEV-{n:03d}"
            value = value_factory(n)
            query = f"What is the current {relation} for {subject}?"
            if block == 0:
                good = f"The current {relation} for {subject} is {value}."
                memories = [
                    _memory("a", good, 10),
                    _memory("b", f"Question about {subject} {relation} remains in the agenda only.", 11),
                    _memory("c", f"The current {relation} for OTHER-{n:03d} is NOISE-{n}.", 12),
                ]
            elif block == 1:
                good = f"{subject} current {relation} is {value}."
                memories = [
                    _memory("a", good, 10),
                    _memory("b", f"Review of the current {relation} for {subject} is a topic only.", 11),
                ]
            elif block == 2:
                good = f"{subject}'s current {relation} is {value}."
                memories = [
                    _memory("a", good, 10),
                    _memory("b", f"Review of the current {relation} for {subject} contains no recorded value.", 11),
                ]
            elif block == 3:
                good = f"The {relation} for {subject} updated to {value}."
                memories = [
                    _memory("a", good, 12),
                    _memory("b", f"The old {relation} for {subject} was OLD-{n}.", 3),
                ]
            else:
                good = f"The current {relation} for {subject} is {value}."
                memories = [
                    _memory("a", good, 12),
                    _memory("b", f"The old {relation} for {subject} was OLD-{n}.", 3),
                    _memory("c", f"Question about {subject} {relation} remains in the agenda only.", 11),
                ]
            cases.append(
                _case(
                    f"dev-a-{n:03d}",
                    "answerable",
                    query,
                    memories,
                    ["a"],
                    [{"memory_id": "a", "expected_assertion_type": "ASSERTED_VALUE", "diagnostic_family": "assertion_extraction"}],
                    "SUPPORTED",
                )
            )

    # 10 agenda-only historical-mechanism regressions, newly authored.
    for i, (relation, _) in enumerate(RELATIONS, 1):
        n = 50 + i
        subject = f"DEV-{n:03d}"
        query = f"Which current {relation} is recorded for {subject}?"
        text = f"Question about {subject} {relation} remains in the agenda only."
        cases.append(
            _case(
                f"dev-n-{n:03d}", "agenda_only", query,
                [_memory("a", text), _memory("b", f"{subject} {relation} review topic only.")], [],
                [{"memory_id": "a", "expected_assertion_type": "AGENDA_ITEM", "diagnostic_family": "meta_discourse"}],
                "INSUFFICIENT",
            )
        )

    # 10 review-topic regressions.
    for i, (relation, _) in enumerate(RELATIONS, 1):
        n = 60 + i
        subject = f"DEV-{n:03d}"
        query = f"What is the current {relation} for {subject}?"
        text = f"Review of the current {relation} for {subject} is a discussion topic only."
        cases.append(
            _case(
                f"dev-n-{n:03d}", "review_topic", query,
                [_memory("a", text), _memory("b", f"{subject} current {relation} review topic only.")], [],
                [{"memory_id": "a", "expected_assertion_type": "REVIEW_TOPIC", "diagnostic_family": "meta_discourse"}],
                "INSUFFICIENT",
            )
        )

    # 10 explicit absence-of-value cases.
    for i, (relation, _) in enumerate(RELATIONS, 1):
        n = 70 + i
        subject = f"DEV-{n:03d}"
        query = f"What is the current {relation} for {subject}?"
        text = f"Review of the current {relation} for {subject} contains no recorded value."
        cases.append(
            _case(
                f"dev-n-{n:03d}", "explicit_no_value", query,
                [_memory("a", text), _memory("b", f"The {relation} question for {subject} has no known answer.")], [],
                [{"memory_id": "a", "expected_assertion_type": "NO_VALUE_RECORDED", "diagnostic_family": "explicit_no_value"}],
                "INSUFFICIENT",
            )
        )

    # 10 wrong-subject cases.
    for i, (relation, value_factory) in enumerate(RELATIONS, 1):
        n = 80 + i
        subject = f"DEV-{n:03d}"
        query = f"What is the current {relation} for {subject}?"
        text = f"The current {relation} for OTHER-{n:03d} is {value_factory(n)}."
        cases.append(
            _case(
                f"dev-n-{n:03d}", "wrong_subject", query,
                [_memory("a", text), _memory("b", f"Question about {subject} {relation} remains open.")], [],
                [{"memory_id": "a", "expected_assertion_type": "UNKNOWN", "diagnostic_family": "assertion_extraction"}],
                "INSUFFICIENT",
            )
        )

    # 10 wrong-relation cases.
    for i, (relation, _) in enumerate(RELATIONS, 1):
        n = 90 + i
        subject = f"DEV-{n:03d}"
        other_relation = RELATIONS[i % len(RELATIONS)][0]
        query = f"What is the current {relation} for {subject}?"
        text = f"The current {other_relation} for {subject} is NOISE-{n}."
        cases.append(
            _case(
                f"dev-n-{n:03d}", "wrong_relation", query,
                [_memory("a", text), _memory("b", f"Question about {subject} {relation} remains open.")], [],
                [{"memory_id": "a", "expected_assertion_type": "UNKNOWN", "diagnostic_family": "assertion_extraction"}],
                "INSUFFICIENT",
            )
        )

    # 5 inferential, 5 negative, 5 stale-only, 5 true contradictions.
    for j in range(5):
        relation = RELATIONS[j][0]
        n = 101 + j
        subject = f"DEV-{n:03d}"
        query = f"What is the current {relation} for {subject}?"
        text = f"The current {relation} for {subject} is probably GUESS-{n}."
        cases.append(_case(
            f"dev-n-{n:03d}", "unsupported_inference", query, [_memory("a", text)], [],
            [{"memory_id": "a", "expected_assertion_type": "UNRESOLVED", "diagnostic_family": "meta_discourse"}], "INSUFFICIENT"
        ))

    for j in range(5):
        relation = RELATIONS[j + 5][0]
        n = 106 + j
        subject = f"DEV-{n:03d}"
        query = f"What is the current {relation} for {subject}?"
        text = f"The current {relation} for {subject} is not BAD-{n}."
        cases.append(_case(
            f"dev-n-{n:03d}", "negative_assertion", query, [_memory("a", text)], [],
            [{"memory_id": "a", "expected_assertion_type": "NEGATED_VALUE", "diagnostic_family": "meta_discourse"}], "INSUFFICIENT"
        ))

    for j in range(5):
        relation, value_factory = RELATIONS[j]
        n = 111 + j
        subject = f"DEV-{n:03d}"
        query = f"What is the current {relation} for {subject}?"
        text = f"The old {relation} for {subject} was {value_factory(n)}."
        cases.append(_case(
            f"dev-n-{n:03d}", "stale_only", query, [_memory("a", text, 2)], [],
            [{"memory_id": "a", "expected_assertion_type": "ASSERTED_VALUE", "diagnostic_family": "temporal_resolution"}], "INSUFFICIENT"
        ))

    for j in range(5):
        relation = RELATIONS[j + 5][0]
        n = 116 + j
        subject = f"DEV-{n:03d}"
        query = f"What is the current {relation} for {subject}?"
        a = f"The current {relation} for {subject} is VALUE-A-{n}."
        b = f"The current {relation} for {subject} is VALUE-B-{n}."
        cases.append(_case(
            f"dev-n-{n:03d}", "contradiction", query, [_memory("a", a, 10), _memory("b", b, 10)], [],
            [
                {"memory_id": "a", "expected_assertion_type": "ASSERTED_VALUE", "diagnostic_family": "contradiction_detection"},
                {"memory_id": "b", "expected_assertion_type": "ASSERTED_VALUE", "diagnostic_family": "contradiction_detection"},
            ],
            "CONTRADICTED",
        ))

    if len(cases) != 120:
        raise AssertionError(f"unexpected case count: {len(cases)}")
    if sum(bool(case["relevant_memory_ids"]) for case in cases) != 50:
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
