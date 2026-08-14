from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.zero_cost_baselines import evaluate_cases, pse_candidate_v1_rank, pse_current_rank

ROOT = Path(__file__).resolve().parents[1]
ADV = ROOT / "benchmarks/algorithm-development/adversarial-v3"
ORIGINAL = ROOT / "benchmarks/strong-baseline/synthetic-memory-cases-v1.json"
RESULTS = ROOT / "results/candidate-v2"


def load_cases(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


class CandidateV2SummaryTests(unittest.TestCase):
    def test_core_metrics_reconstruct_from_frozen_inputs(self) -> None:
        summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
        splits = {
            "adversarial_development": load_cases(ADV / "development.json"),
            "adversarial_validation": load_cases(ADV / "validation.json"),
            "adversarial_withheld": load_cases(ADV / "withheld.json"),
            "original_24": load_cases(ORIGINAL),
        }
        systems = {
            "pse_current_reconstruction": pse_current_rank,
            "pse_candidate_v1": pse_candidate_v1_rank,
            "pse_candidate_v2": pse_candidate_v2_rank,
        }
        for split, cases in splits.items():
            for system, ranker in systems.items():
                observed = evaluate_cases(cases, ranker)["metrics"]
                expected = summary["metrics"][split][system]
                for key, value in expected.items():
                    self.assertAlmostEqual(observed[key], value, places=12, msg=f"{split}/{system}/{key}")

    def test_post_freeze_withheld_and_tradeoff_are_preserved(self) -> None:
        summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
        held = summary["metrics"]["adversarial_withheld"]
        normal = summary["metrics"]["original_24"]
        self.assertGreater(held["pse_candidate_v2"]["MRR"], held["pse_candidate_v1"]["MRR"])
        self.assertEqual(held["pse_candidate_v2"]["recall@5"], 1.0)
        self.assertEqual(held["pse_candidate_v2"]["abstention_accuracy"], 0.0)
        self.assertLess(normal["pse_candidate_v2"]["MRR"], normal["pse_candidate_v1"]["MRR"])
        self.assertGreater(normal["pse_candidate_v2"]["MRR"], normal["pse_current_reconstruction"]["MRR"])
        self.assertFalse(summary["tuning_after_withheld"])
        self.assertFalse(summary["independent_reproduction"])
        self.assertEqual(summary["algorithm_parity"], "NO")

    def test_artifact_registry_is_fail_closed(self) -> None:
        registry = json.loads((RESULTS / "artifact-registry.json").read_text(encoding="utf-8"))
        self.assertFalse(registry["sealed_final_accessed"])
        self.assertEqual(registry["artifact_count"], len(registry["artifacts"]))
        for artifact in registry["artifacts"]:
            path = ROOT / artifact["path"]
            self.assertTrue(path.exists(), artifact["path"])
            self.assertEqual(path.stat().st_size, artifact["bytes"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
