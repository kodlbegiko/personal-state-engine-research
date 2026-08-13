from __future__ import annotations

import unittest

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v6 import (
    AGENDA_ITEM,
    ASSERTED_VALUE,
    NEGATED_VALUE,
    NO_VALUE_RECORDED,
    QUESTION,
    REVIEW_TOPIC,
    UNRESOLVED,
    VERDICT_CONTRADICTED,
    VERDICT_INSUFFICIENT,
    VERDICT_SUPPORTED,
    answerability_signature,
    classify_discourse_role,
    parse_evidence_object,
    pse_candidate_v6_rank,
)


def _m(mid: str, text: str, day: int = 7) -> dict:
    return {"id": mid, "text": text, "timestamp": f"2026-08-{day:02d}T10:00:00+00:00"}


def _case(query: str, memories: list[dict], relevant: list[str] | None = None) -> dict:
    return {
        "id": "unit-v6",
        "category": "unit",
        "query": query,
        "memories": memories,
        "relevant_memory_ids": relevant or [],
    }


class CandidateV6Tests(unittest.TestCase):
    def test_true_assertion_relation_for_subject(self) -> None:
        case = _case("What is the current email for Entity-101?", [_m("a", "The current email for Entity-101 is alpha@example.test.")])
        obj = parse_evidence_object(case["memories"][0], case["query"])
        self.assertEqual(obj.assertion_type, ASSERTED_VALUE)
        self.assertEqual(obj.predicate, "email")
        self.assertEqual(answerability_signature(case)["verdict"], VERDICT_SUPPORTED)

    def test_true_assertion_subject_relation(self) -> None:
        case = _case("What is the current code for VAL-101?", [_m("a", "VAL-101 current code is VX-804.")])
        self.assertEqual(answerability_signature(case)["verdict"], VERDICT_SUPPORTED)

    def test_possessive_assertion(self) -> None:
        case = _case("What is the current provider for VAL-101?", [_m("a", "VAL-101's current provider is AsterWorks.")])
        self.assertEqual(answerability_signature(case)["verdict"], VERDICT_SUPPORTED)

    def test_update_assertion(self) -> None:
        case = _case("What is the current version for VAL-101?", [_m("a", "The version for VAL-101 updated to v8.1.")])
        obj = parse_evidence_object(case["memories"][0], case["query"])
        self.assertEqual(obj.assertion_type, ASSERTED_VALUE)
        self.assertTrue(obj.resolving)

    def test_wrong_subject_abstains(self) -> None:
        case = _case("What is the current phone for Entity-101?", [_m("a", "The current phone for Entity-202 is +1-555-0101.")])
        self.assertEqual(pse_candidate_v6_rank(case), [])

    def test_wrong_predicate_abstains(self) -> None:
        case = _case("What is the current email for Entity-101?", [_m("a", "The current phone for Entity-101 is +1-555-0101.")])
        self.assertEqual(pse_candidate_v6_rank(case), [])

    def test_invalid_value_is_negative(self) -> None:
        case = _case("What is the current code for Entity-101?", [_m("a", "ZX-41 is an invalid code for Entity-101; do not use it.")])
        obj = parse_evidence_object(case["memories"][0], case["query"])
        self.assertEqual(obj.assertion_type, NEGATED_VALUE)
        self.assertEqual(pse_candidate_v6_rank(case), [])

    def test_query_echo_abstains(self) -> None:
        q = "What is the current status for Entity-101?"
        case = _case(q, [_m("a", q)])
        self.assertEqual(parse_evidence_object(case["memories"][0], q).assertion_type, QUESTION)
        self.assertEqual(pse_candidate_v6_rank(case), [])

    def test_question_about_relation_is_not_value(self) -> None:
        q = "Which current code is recorded for VAL-013?"
        memory = _m("a", "Question about VAL-013 code remains open.")
        obj = parse_evidence_object(memory, q)
        self.assertEqual(obj.assertion_type, QUESTION)
        self.assertIsNone(obj.object_or_value)

    def test_agenda_item_is_not_value(self) -> None:
        q = "Which current code is recorded for VAL-013?"
        memory = _m("a", "Question about VAL-013 code remains in the agenda only.")
        obj = parse_evidence_object(memory, q)
        self.assertEqual(obj.assertion_type, AGENDA_ITEM)
        self.assertIsNone(obj.object_or_value)

    def test_agenda_noise_does_not_conflict_with_answer(self) -> None:
        q = "Which current code is recorded for VAL-013?"
        case = _case(q, [_m("meta", "Question about VAL-013 code remains in the agenda only."), _m("good", "The current code for VAL-013 is VX-804.")])
        self.assertEqual(answerability_signature(case)["verdict"], VERDICT_SUPPORTED)

    def test_review_topic_is_not_value(self) -> None:
        q = "What is the current time for VAL-045?"
        memory = _m("a", "Review of the current time for VAL-045 is a discussion topic only.")
        obj = parse_evidence_object(memory, q)
        self.assertEqual(obj.assertion_type, REVIEW_TOPIC)
        self.assertIsNone(obj.object_or_value)

    def test_explicit_no_value_is_detected(self) -> None:
        q = "What is the current email for VAL-046?"
        memory = _m("a", "Review of the current email for VAL-046 contains no recorded value.")
        obj = parse_evidence_object(memory, q)
        self.assertEqual(obj.assertion_type, NO_VALUE_RECORDED)
        self.assertIsNone(obj.object_or_value)

    def test_explicit_no_answer_present(self) -> None:
        q = "What is the current version for Entity-101?"
        memory = _m("a", "The current version for Entity-101 is under review; answer not present.")
        self.assertEqual(parse_evidence_object(memory, q).assertion_type, NO_VALUE_RECORDED)
        self.assertEqual(pse_candidate_v6_rank(_case(q, [memory])), [])

    def test_relation_mention_without_value_abstains(self) -> None:
        q = "What is the current provider for Entity-101?"
        case = _case(q, [_m("a", "Entity-101 provider remains a discussion topic.")])
        self.assertEqual(pse_candidate_v6_rank(case), [])

    def test_value_mention_without_assertion_abstains(self) -> None:
        q = "What is the current code for Entity-101?"
        case = _case(q, [_m("a", "Entity-101 code topic includes the token VX-804 for testing only.")])
        self.assertEqual(pse_candidate_v6_rank(case), [])

    def test_partial_multi_relation_abstains(self) -> None:
        case = _case(
            "What are the current phone and email for Entity-101?",
            [_m("a", "The current phone for Entity-101 is +1-555-0101."), _m("b", "The email for Entity-101 remains unresolved.")],
        )
        sig = answerability_signature(case)
        self.assertEqual(sig["verdict"], VERDICT_INSUFFICIENT)
        self.assertIn("email", sig["missing_requirements"])

    def test_multi_relation_complete_support(self) -> None:
        case = _case(
            "What are the current phone and email for Entity-101?",
            [_m("a", "The current phone for Entity-101 is +1-555-0101."), _m("b", "The current email for Entity-101 is alpha@example.test.")],
        )
        self.assertEqual(answerability_signature(case)["verdict"], VERDICT_SUPPORTED)

    def test_stale_only_current_query_abstains(self) -> None:
        case = _case("What is the current budget for Entity-101?", [_m("a", "The old budget for Entity-101 was 4800.", 2)])
        self.assertEqual(pse_candidate_v6_rank(case), [])

    def test_current_overrides_stale(self) -> None:
        case = _case(
            "What is the current budget for Entity-101?",
            [_m("old", "The old budget for Entity-101 was 4800.", 2), _m("new", "The current budget for Entity-101 is 5200.", 7)],
        )
        self.assertEqual(answerability_signature(case)["verdict"], VERDICT_SUPPORTED)

    def test_unresolved_inference_abstains(self) -> None:
        case = _case("What is the current owner for Entity-101?", [_m("a", "The owner for Entity-101 is probably Mira.")])
        obj = parse_evidence_object(case["memories"][0], case["query"])
        self.assertEqual(obj.assertion_type, UNRESOLVED)
        self.assertEqual(pse_candidate_v6_rank(case), [])

    def test_unresolved_marker_abstains(self) -> None:
        case = _case("What is the current status for Entity-101?", [_m("a", "The status for Entity-101 remains unresolved.")])
        self.assertEqual(pse_candidate_v6_rank(case), [])

    def test_current_contradiction_abstains(self) -> None:
        case = _case(
            "What is the current color for Entity-101?",
            [_m("a", "The current color for Entity-101 is amber.", 7), _m("b", "The current color for Entity-101 is cobalt.", 7)],
        )
        self.assertEqual(answerability_signature(case)["verdict"], VERDICT_CONTRADICTED)
        self.assertEqual(pse_candidate_v6_rank(case), [])

    def test_resolving_update_supports(self) -> None:
        case = _case(
            "What is the current color for Entity-101?",
            [_m("a", "The old color for Entity-101 was amber.", 2), _m("b", "Correction: Entity-101 color changed to cobalt.", 7)],
        )
        self.assertEqual(answerability_signature(case)["verdict"], VERDICT_SUPPORTED)

    def test_negative_assertion_does_not_support(self) -> None:
        case = _case("What is the current provider for Entity-101?", [_m("a", "The provider for Entity-101 is not AsterWorks.")])
        self.assertEqual(pse_candidate_v6_rank(case), [])

    def test_same_subject_wrong_attribute_abstains(self) -> None:
        case = _case("What is the current code for Entity-101?", [_m("a", "The current version for Entity-101 is v8.1.")])
        self.assertEqual(pse_candidate_v6_rank(case), [])

    def test_same_attribute_wrong_subject_abstains(self) -> None:
        case = _case("What is the current code for Entity-101?", [_m("a", "The current code for Entity-202 is VX-804.")])
        self.assertEqual(pse_candidate_v6_rank(case), [])

    def test_unrelated_distractor_does_not_change_supported_verdict(self) -> None:
        q = "What is the current code for Entity-101?"
        base = _case(q, [_m("good", "The current code for Entity-101 is VX-804.")])
        noisy = _case(q, [_m("good", "The current code for Entity-101 is VX-804."), _m("noise", "Weather notes for tomorrow are unrelated.", 8)])
        self.assertEqual(answerability_signature(base)["verdict"], VERDICT_SUPPORTED)
        self.assertEqual(answerability_signature(noisy)["verdict"], VERDICT_SUPPORTED)

    def test_memory_reordering_preserves_semantic_verdict(self) -> None:
        q = "What is the current email for Entity-101?"
        a = _m("good", "The current email for Entity-101 is alpha@example.test.")
        b = _m("meta", "Question about Entity-101 email remains in the agenda only.")
        self.assertEqual(answerability_signature(_case(q, [a, b]))["verdict"], answerability_signature(_case(q, [b, a]))["verdict"])

    def test_removing_unique_assertion_causes_abstention(self) -> None:
        q = "What is the current email for Entity-101?"
        good = _m("good", "The current email for Entity-101 is alpha@example.test.")
        meta = _m("meta", "Question about Entity-101 email remains in the agenda only.")
        self.assertEqual(answerability_signature(_case(q, [good, meta]))["verdict"], VERDICT_SUPPORTED)
        self.assertEqual(pse_candidate_v6_rank(_case(q, [meta])), [])

    def test_meta_overlap_cannot_create_assertion(self) -> None:
        q = "What is the current time for VAL-045?"
        text = "VAL-045 current time current VAL-045 time review topic only."
        role, _ = classify_discourse_role(text)
        self.assertNotEqual(role, "ASSERTION")
        self.assertEqual(pse_candidate_v6_rank(_case(q, [_m("a", text)])), [])

    def test_candidate_v2_ranking_preserved_when_supported(self) -> None:
        case = _case(
            "What is the current email for Entity-101?",
            [
                _m("a", "The current email for Entity-101 is alpha@example.test.", 7),
                _m("b", "The current email for Other-999 is beta@example.test.", 8),
                _m("c", "Unrelated logistics for Entity-101.", 8),
            ],
        )
        self.assertEqual(pse_candidate_v6_rank(case, 5), pse_candidate_v2_rank(case, 5))

    def test_fail_closed_on_unparsed_statement(self) -> None:
        q = "What is the current code for Entity-101?"
        memory = _m("a", "For Entity-101, VX-804 somehow corresponds to code in prose.")
        obj = parse_evidence_object(memory, q)
        self.assertEqual(obj.parse_status, "FAIL_CLOSED")
        self.assertEqual(pse_candidate_v6_rank(_case(q, [memory])), [])


if __name__ == "__main__":
    unittest.main()
