from __future__ import annotations

import unittest

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v5 import (
    VERDICT_CONTRADICTED,
    VERDICT_INSUFFICIENT,
    VERDICT_SUPPORTED,
    answerability_signature,
    pse_candidate_v5_rank,
)


def _m(mid: str, text: str, day: int = 7) -> dict:
    return {"id": mid, "text": text, "timestamp": f"2026-08-{day:02d}T10:00:00+00:00"}


def _case(query: str, memories: list[dict]) -> dict:
    return {"id": "unit-v5", "category": "unit", "query": query, "memories": memories, "relevant_memory_ids": []}


class CandidateV5Tests(unittest.TestCase):
    def test_supported_single_evidence(self) -> None:
        case = _case("What is the current email for Entity-101?", [_m("a", "The current email for Entity-101 is alpha@example.test.")])
        self.assertEqual(answerability_signature(case)["verdict"], VERDICT_SUPPORTED)
        self.assertTrue(pse_candidate_v5_rank(case))

    def test_wrong_subject_abstains(self) -> None:
        case = _case("What is the current phone for Entity-101?", [_m("a", "The current phone for Entity-202 is +1-555-0101.")])
        self.assertEqual(pse_candidate_v5_rank(case), [])

    def test_wrong_predicate_abstains(self) -> None:
        case = _case("What is the current email for Entity-101?", [_m("a", "The current phone for Entity-101 is +1-555-0101.")])
        self.assertEqual(pse_candidate_v5_rank(case), [])

    def test_wrong_value_marked_invalid_abstains(self) -> None:
        case = _case("What is the current code for Entity-101?", [_m("a", "ZX-41 is a wrong code for Entity-101; do not use it.")])
        self.assertEqual(pse_candidate_v5_rank(case), [])

    def test_stale_only_abstains(self) -> None:
        case = _case("What is the current budget for Entity-101?", [_m("a", "The old stale budget for Entity-101 was 4800.", 2)])
        self.assertEqual(pse_candidate_v5_rank(case), [])

    def test_stale_plus_fresh_answers(self) -> None:
        case = _case(
            "What is the current budget for Entity-101?",
            [_m("old", "The old stale budget for Entity-101 was 4800.", 2), _m("new", "The current budget for Entity-101 is 5200.", 7)],
        )
        self.assertEqual(answerability_signature(case)["verdict"], VERDICT_SUPPORTED)

    def test_query_echo_abstains(self) -> None:
        q = "What is the current status for Entity-101?"
        case = _case(q, [_m("a", q), _m("b", f"Question repeated: {q}")])
        self.assertEqual(pse_candidate_v5_rank(case), [])

    def test_partial_evidence_abstains(self) -> None:
        case = _case(
            "What are the current phone and email for Entity-101?",
            [_m("a", "The current phone for Entity-101 is +1-555-0101."), _m("b", "The email question for Entity-101 remains unresolved.")],
        )
        sig = answerability_signature(case)
        self.assertEqual(sig["verdict"], VERDICT_INSUFFICIENT)
        self.assertIn("email", sig["missing_requirements"])

    def test_unresolved_contradiction_abstains(self) -> None:
        case = _case(
            "What is the current color for Entity-101?",
            [_m("a", "The color for Entity-101 is amber.", 6), _m("b", "The color for Entity-101 is cobalt.", 6)],
        )
        self.assertEqual(answerability_signature(case)["verdict"], VERDICT_CONTRADICTED)
        self.assertEqual(pse_candidate_v5_rank(case), [])

    def test_resolved_contradiction_answers(self) -> None:
        case = _case(
            "What is the current color for Entity-101?",
            [_m("a", "The old color for Entity-101 was amber.", 2), _m("b", "Correction: Entity-101 color changed to cobalt; this replaces the old value.", 7)],
        )
        self.assertEqual(answerability_signature(case)["verdict"], VERDICT_SUPPORTED)

    def test_unsupported_inference_abstains(self) -> None:
        case = _case("What is the current owner for Entity-101?", [_m("a", "The owner for Entity-101 is probably Mira.")])
        self.assertEqual(pse_candidate_v5_rank(case), [])

    def test_temporal_near_match_abstains(self) -> None:
        case = _case("What is the current salary for Entity-101?", [_m("a", "Before the current period, the salary for Entity-101 was 42000.", 2)])
        self.assertEqual(pse_candidate_v5_rank(case), [])

    def test_near_duplicate_abstains(self) -> None:
        case = _case("What is the current version for Entity-101?", [_m("a", "Please record the question: what is the current version for Entity-101; answer not present.")])
        self.assertEqual(pse_candidate_v5_rank(case), [])

    def test_multi_slot_complete_support_answers(self) -> None:
        case = _case(
            "What are the current phone and email for Entity-101?",
            [_m("a", "The current phone for Entity-101 is +1-555-0101."), _m("b", "The current email for Entity-101 is alpha@example.test.")],
        )
        self.assertEqual(answerability_signature(case)["verdict"], VERDICT_SUPPORTED)

    def test_multi_slot_partial_support_abstains(self) -> None:
        case = _case("What are the current budget and balance for Entity-101?", [_m("a", "The current budget for Entity-101 is 4800.")])
        self.assertEqual(pse_candidate_v5_rank(case), [])

    def test_candidate_v2_ranking_preserved_when_supported(self) -> None:
        case = _case(
            "What is the current email for Entity-101?",
            [
                _m("a", "The current email for Entity-101 is alpha@example.test.", 7),
                _m("b", "The current email for Other-999 is beta@example.test.", 8),
                _m("c", "Unrelated logistics for Entity-101.", 8),
            ],
        )
        self.assertEqual(pse_candidate_v5_rank(case, 5), pse_candidate_v2_rank(case, 5))


if __name__ == "__main__":
    unittest.main()
