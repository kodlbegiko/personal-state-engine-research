from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.run_redteam import run


class RedTeamPolicyTests(unittest.TestCase):
    def test_corpus_has_both_attacks_and_benign_controls(self):
        rows = [json.loads(line) for line in Path("benchmarks/redteam/memory-write-policy.jsonl").read_text().splitlines()]
        self.assertTrue(any(row["expected_allowed"] is False for row in rows))
        self.assertTrue(any(row["expected_allowed"] is True for row in rows))
        self.assertEqual(len(rows), len({row["id"] for row in rows}))

    def test_current_policy_matches_frozen_corpus(self):
        _, _, summary = run()
        self.assertEqual(summary["passed"], summary["cases"])
        self.assertEqual(summary["false_negative"], 0)
        self.assertEqual(summary["false_positive"], 0)


if __name__ == "__main__":
    unittest.main()
