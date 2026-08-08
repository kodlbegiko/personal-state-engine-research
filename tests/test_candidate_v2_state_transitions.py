from __future__ import annotations

import unittest

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank


class CandidateV2StateTransitionTests(unittest.TestCase):
    def assert_top(self, query: str, older: str, newer: str) -> None:
        case = {
            "id": "generic-transition",
            "memories": [
                {"id": "old", "text": older, "timestamp": "2025-01-01"},
                {"id": "new", "text": newer, "timestamp": "2026-06-01"},
            ],
            "query": query,
            "relevant_memory_ids": ["new"],
        }
        self.assertEqual(pse_candidate_v2_rank(case)[0], "new")

    def test_explicit_correction_supersedes_old_value(self) -> None:
        self.assert_top("What is the current room?", "Room is 301", "Corrected room: 402")

    def test_preference_reversal(self) -> None:
        self.assert_top("What drink is preferred now?", "User prefers coffee", "User stopped coffee and now prefers tea")

    def test_revoked_preference(self) -> None:
        self.assert_top("Are email alerts still preferred?", "User prefers email alerts", "User revoked email alerts and changed to SMS")

    def test_rescheduled_event(self) -> None:
        self.assert_top("When is the meeting now?", "Meeting is Monday at 10", "Meeting rescheduled to Tuesday at 14")

    def test_moved_location(self) -> None:
        self.assert_top("Where is the desk now?", "Desk is on floor 3", "Desk moved to floor 5")

    def test_same_entity_updated_attribute(self) -> None:
        self.assert_top("What is Project Orion's current owner?", "Project Orion owner is Dana", "Project Orion owner changed to Mei")


if __name__ == "__main__":
    unittest.main()
