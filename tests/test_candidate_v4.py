from __future__ import annotations

import unittest

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v4 import VERDICT_INSUFFICIENT, VERDICT_SUPPORTED, answerability_signature, pse_candidate_v4_rank

class CandidateV4Tests(unittest.TestCase):
    def test_supported_case_preserves_frozen_v2_order(self) -> None:
        case = {"id":"unit-supported","query":"What is the Orion project budget?","memories":[{"id":"m1","text":"The approved Orion project budget is 420000.","timestamp":"2026-06-02"},{"id":"m2","text":"Orion owner is Dana.","timestamp":"2026-06-03"}],"relevant_memory_ids":["m1"]}
        self.assertEqual(pse_candidate_v4_rank(case, 5), pse_candidate_v2_rank(case, 5))
        self.assertEqual(answerability_signature(case)["verdict"], VERDICT_SUPPORTED)

    def test_same_entity_wrong_field_fails_closed(self) -> None:
        case = {"id":"unit-wrong-field","query":"What is Project Nova's budget?","memories":[{"id":"m1","text":"Project Nova owner is Alice.","timestamp":"2026-06-01"}],"relevant_memory_ids":[]}
        self.assertEqual(pse_candidate_v4_rank(case, 5), [])
        self.assertEqual(answerability_signature(case)["verdict"], VERDICT_INSUFFICIENT)

    def test_temporal_constraint_must_match(self) -> None:
        case = {"id":"unit-temporal","query":"What was the April sales total?","memories":[{"id":"m1","text":"March sales total was 88000.","timestamp":"2026-03-31"}],"relevant_memory_ids":[]}
        self.assertEqual(pse_candidate_v4_rank(case, 5), [])

    def test_certainty_query_rejects_tentative_evidence(self) -> None:
        case = {"id":"unit-certainty","query":"What is the confirmed workshop room?","memories":[{"id":"m1","text":"The workshop might be in Room A.","timestamp":"2026-06-01"},{"id":"m2","text":"The workshop might be in Room B.","timestamp":"2026-06-01"}],"relevant_memory_ids":[]}
        self.assertEqual(pse_candidate_v4_rank(case, 5), [])

    def test_question_echo_is_not_evidence(self) -> None:
        case = {"id":"unit-echo","query":"What is the private vault PIN?","memories":[{"id":"m1","text":"What is the private vault PIN?","timestamp":"2026-06-01"}],"relevant_memory_ids":[]}
        self.assertEqual(pse_candidate_v4_rank(case, 5), [])

    def test_license_number_not_supported_by_renewal_office(self) -> None:
        case = {"id":"unit-license","query":"What is the driver's license number?","memories":[{"id":"m1","text":"Driver license renewal office is downtown.","timestamp":"2026-01-01"}],"relevant_memory_ids":[]}
        self.assertEqual(pse_candidate_v4_rank(case, 5), [])

if __name__ == "__main__":
    unittest.main()
