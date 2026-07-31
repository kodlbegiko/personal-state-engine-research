from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.analyze_component_results import analyze


class AnalysisPipelineTests(unittest.TestCase):
    def test_analysis_emits_all_baselines_and_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            path, report = analyze(output_path=Path(directory) / "statistics.json")
            self.assertTrue(path.exists())
            self.assertEqual(set(report["baseline_summaries"]), {f"B{i}" for i in range(8)})
            self.assertIn("not_model_efficacy", report["interpretation"])

    def test_b0_b7_comparison_is_paired(self):
        with tempfile.TemporaryDirectory() as directory:
            _, report = analyze(output_path=Path(directory) / "statistics.json")
            comparison = report["paired_against_B0"]["B0_vs_B7"]
            self.assertEqual(comparison["pairs"], 9)
            self.assertGreater(comparison["difference"], 0)


if __name__ == "__main__":
    unittest.main()
