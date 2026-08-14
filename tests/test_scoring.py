from __future__ import annotations

import unittest

from personal_state_engine.scoring import (
    StructuredOutcomeScorer,
    paired_mcnemar,
    summarise_binary,
    wilson_interval,
)


class ScoringTests(unittest.TestCase):
    def test_structured_scorer_accepts_required_subset(self):
        decision = StructuredOutcomeScorer().score(
            {"status": "completed", "memory": {"value": "new"}},
            {"status": "completed", "memory": {"value": "new", "source": "user"}, "extra": 1},
        )
        self.assertTrue(decision.passed)

    def test_structured_scorer_reports_path(self):
        decision = StructuredOutcomeScorer().score(
            {"status": "completed", "memory": {"value": "new"}},
            {"status": "completed", "memory": {"value": "old"}},
        )
        self.assertFalse(decision.passed)
        self.assertIn("$.memory.value", decision.reasons[0])

    def test_wilson_interval_bounds_rate(self):
        summary = wilson_interval(8, 10)
        self.assertLess(summary.lower_95, summary.rate)
        self.assertGreater(summary.upper_95, summary.rate)

    def test_binary_summary(self):
        summary = summarise_binary([True, False, True, True])
        self.assertEqual(summary.n, 4)
        self.assertEqual(summary.successes, 3)
        self.assertEqual(summary.rate, 0.75)

    def test_paired_comparison_detects_direction(self):
        comparison = paired_mcnemar(
            {"a": False, "b": False, "c": True, "d": False},
            {"a": True, "b": True, "c": True, "d": False},
        )
        self.assertEqual(comparison.left_only, 0)
        self.assertEqual(comparison.right_only, 2)
        self.assertEqual(comparison.difference, 0.5)

    def test_paired_comparison_requires_same_keys(self):
        with self.assertRaises(ValueError):
            paired_mcnemar({"a": True}, {"b": True})


if __name__ == "__main__":
    unittest.main()
