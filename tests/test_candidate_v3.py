from __future__ import annotations

import unittest

from personal_state_engine.candidate_v3 import (
    evidence_supports_query,
    pse_candidate_v3_rank,
    relation_concepts,
)


class CandidateV3Tests(unittest.TestCase):
    def test_relation_slots_keep_adjacent_fields_distinct(self) -> None:
        self.assertIn("email", relation_concepts("What is the account email?"))
        self.assertIn("phone", relation_concepts("What is the account phone?"))
        self.assertFalse(
            evidence_supports_query("Account phone is 555-0100", "What is the account email?")
        )

    def test_same_entity_wrong_field_abstains(self) -> None:
        case = {
            "id": "GEN-N01",
            "query": "What is Project Vega's budget?",
            "memories": [{"id": "m1", "text": "Project Vega owner is Mina", "timestamp": "2026-01-01"}],
            "relevant_memory_ids": [],
        }
        self.assertEqual(pse_candidate_v3_rank(case), [])

    def test_question_echo_abstains(self) -> None:
        case = {
            "id": "GEN-N02",
            "query": "What is the vault PIN?",
            "memories": [{"id": "m1", "text": "What is the vault PIN?", "timestamp": "2026-01-01"}],
            "relevant_memory_ids": [],
        }
        self.assertEqual(pse_candidate_v3_rank(case), [])

    def test_confirmed_query_rejects_only_uncertain_evidence(self) -> None:
        case = {
            "id": "GEN-N03",
            "query": "What is the confirmed event date?",
            "memories": [
                {"id": "m1", "text": "Event date might be June 3", "timestamp": "2026-01-01"},
                {"id": "m2", "text": "Event date may be June 4", "timestamp": "2026-01-01"},
            ],
            "relevant_memory_ids": [],
        }
        self.assertEqual(pse_candidate_v3_rank(case), [])

    def test_supported_value_preserves_frozen_v2_order(self) -> None:
        case = {
            "id": "GEN-A01",
            "query": "What is the device serial number?",
            "memories": [
                {"id": "m1", "text": "Device serial number is ZX-42", "timestamp": "2026-01-01"},
                {"id": "m2", "text": "Device color is blue", "timestamp": "2026-07-01"},
            ],
            "relevant_memory_ids": ["m1"],
        }
        self.assertEqual(pse_candidate_v3_rank(case)[0], "m1")

    def test_cjk_wrong_attribute_abstains(self) -> None:
        case = {
            "id": "GEN-N04",
            "query": "駕照號碼是多少？",
            "memories": [{"id": "m1", "text": "駕照換發地點在市中心", "timestamp": "2026-01-01"}],
            "relevant_memory_ids": [],
        }
        self.assertEqual(pse_candidate_v3_rank(case), [])

    def test_cjk_supported_shop_returns_memory(self) -> None:
        case = {
            "id": "GEN-A02",
            "query": "常用的咖啡店是哪一間？",
            "memories": [{"id": "m1", "text": "常用的咖啡店是慢慢咖啡", "timestamp": "2026-01-01"}],
            "relevant_memory_ids": ["m1"],
        }
        self.assertEqual(pse_candidate_v3_rank(case), ["m1"])


if __name__ == "__main__":
    unittest.main()
