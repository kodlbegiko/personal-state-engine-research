from __future__ import annotations

import unittest

from personal_state_engine.evaluation import run_benchmark, summarise
from personal_state_engine.verification import ActionResult, VerificationLoop


class VerificationTests(unittest.TestCase):
    def test_tool_success_without_evidence_is_false_completion(self):
        result = VerificationLoop().verify(
            ActionResult(True, True, None, "file exists", "file missing")
        )
        self.assertFalse(result.verified)
        self.assertTrue(result.false_completion)

    def test_matching_observed_effect_is_verified(self):
        result = VerificationLoop().verify(
            ActionResult(True, True, "sha-123", "file exists", "file exists")
        )
        self.assertTrue(result.verified)
        self.assertFalse(result.false_completion)

    def test_benchmark_has_all_baselines_and_scenarios(self):
        results = run_benchmark()
        self.assertEqual(len(results), 8 * 9)
        self.assertEqual({item.baseline for item in results}, {f"B{i}" for i in range(8)})

    def test_b7_outperforms_b0_in_component_benchmark(self):
        summary = summarise(run_benchmark())
        self.assertGreater(summary["B7"]["pass_rate"], summary["B0"]["pass_rate"])

    def test_only_b7_rejects_false_completion(self):
        results = [item for item in run_benchmark() if item.scenario == "false_completion_rejection"]
        passing = {item.baseline for item in results if item.passed}
        self.assertEqual(passing, {"B7"})


if __name__ == "__main__":
    unittest.main()
