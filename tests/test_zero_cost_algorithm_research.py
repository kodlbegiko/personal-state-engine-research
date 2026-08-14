from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from personal_state_engine.zero_cost_baselines import (
    RANKERS,
    evaluate_cases,
    pse_candidate_v1_rank,
    pse_current_rank,
)

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "benchmarks/strong-baseline/synthetic-memory-cases-v1.json"
SPEC = ROOT / "benchmarks/algorithm-development/specification-v2.json"
EXT = ROOT / "benchmarks/algorithm-development/withheld-extension-v2.json"
FREEZE = ROOT / "benchmarks/algorithm-development/freeze-manifest-v2.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ZeroCostAlgorithmResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dev = load(DEV)["cases"]
        ext = load(EXT)["cases"]
        cls.validation = [case for case in ext if case["split"] == "validation"]
        cls.hidden = [case for case in ext if case["split"] == "hidden-generated"]

    def test_benchmark_freeze_is_exact(self):
        freeze = load(FREEZE)
        self.assertEqual(sha256(DEV), freeze["development_source"]["sha256"])
        self.assertEqual(sha256(SPEC), freeze["files"]["benchmarks/algorithm-development/specification-v2.json"])
        self.assertEqual(sha256(EXT), freeze["files"]["benchmarks/algorithm-development/withheld-extension-v2.json"])
        self.assertFalse(freeze["sealed_final_accessed"])
        self.assertFalse(freeze["candidate_evaluation_started_before_freeze"])

    def test_candidate_improves_development_mrr_without_recall_at_5_regression(self):
        current = evaluate_cases(self.dev, pse_current_rank)
        candidate = evaluate_cases(self.dev, pse_candidate_v1_rank)
        self.assertAlmostEqual(current["metrics"]["MRR"], 0.9015151515151515)
        self.assertAlmostEqual(candidate["metrics"]["MRR"], 1.0)
        self.assertEqual(current["metrics"]["recall@5"], 1.0)
        self.assertEqual(candidate["metrics"]["recall@5"], 1.0)

    def test_candidate_generalizes_to_frozen_validation(self):
        current = evaluate_cases(self.validation, pse_current_rank)
        candidate = evaluate_cases(self.validation, pse_candidate_v1_rank)
        self.assertAlmostEqual(current["metrics"]["MRR"], 0.9)
        self.assertAlmostEqual(candidate["metrics"]["MRR"], 1.0)

    def test_hidden_generated_result_is_recorded_but_not_overclaimed(self):
        current = evaluate_cases(self.hidden, pse_current_rank)
        candidate = evaluate_cases(self.hidden, pse_candidate_v1_rank)
        self.assertAlmostEqual(current["metrics"]["MRR"], 0.8333333333333334)
        self.assertAlmostEqual(candidate["metrics"]["MRR"], 0.9166666666666666)
        self.assertEqual(candidate["metrics"]["recall@5"], 1.0)

    def test_candidate_does_not_claim_to_solve_abstention(self):
        current = evaluate_cases(self.dev, pse_current_rank)
        candidate = evaluate_cases(self.dev, pse_candidate_v1_rank)
        self.assertEqual(current["metrics"]["abstention_accuracy"], 0.5)
        self.assertEqual(candidate["metrics"]["abstention_accuracy"], 0.5)

    def test_rankers_are_deterministic_across_three_runs(self):
        for name, ranker in RANKERS.items():
            runs = []
            for _ in range(3):
                payload = json.dumps([ranker(case, 5) for case in self.dev], sort_keys=True).encode("utf-8")
                runs.append(hashlib.sha256(payload).hexdigest())
            self.assertEqual(len(set(runs)), 1, name)

    def test_a_mem_is_not_impersonated_by_local_rankers(self):
        self.assertNotIn("A-MEM", RANKERS)
        self.assertNotIn("amem", {name.casefold() for name in RANKERS})


if __name__ == "__main__":
    unittest.main()
