from __future__ import annotations

import json
import unittest
from pathlib import Path

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.zero_cost_baselines import evaluate_cases, pse_candidate_v1_rank

ROOT = Path(__file__).resolve().parents[1]
ADV = ROOT / "benchmarks/algorithm-development/adversarial-v3"


class PSECandidateV2Tests(unittest.TestCase):
    def load(self, name: str) -> list[dict]:
        return json.loads((ADV / name).read_text(encoding="utf-8"))["cases"]

    def test_candidate_v2_beats_v1_on_frozen_adversarial_development(self) -> None:
        cases = self.load("development.json")
        v1 = evaluate_cases(cases, pse_candidate_v1_rank)
        v2 = evaluate_cases(cases, pse_candidate_v2_rank)
        self.assertGreater(v2["metrics"]["MRR"], v1["metrics"]["MRR"])
        self.assertGreaterEqual(v2["metrics"]["recall@5"], v1["metrics"]["recall@5"])

    def test_candidate_v2_beats_v1_on_frozen_adversarial_validation(self) -> None:
        cases = self.load("validation.json")
        v1 = evaluate_cases(cases, pse_candidate_v1_rank)
        v2 = evaluate_cases(cases, pse_candidate_v2_rank)
        self.assertGreater(v2["metrics"]["MRR"], v1["metrics"]["MRR"])
        self.assertGreaterEqual(v2["metrics"]["recall@5"], v1["metrics"]["recall@5"])

    def test_candidate_v2_is_deterministic(self) -> None:
        cases = self.load("validation.json")
        for case in cases:
            first = pse_candidate_v2_rank(case)
            self.assertEqual(first, pse_candidate_v2_rank(case))
            self.assertEqual(first, pse_candidate_v2_rank(case))

    def test_candidate_v2_does_not_claim_abstention(self) -> None:
        cases = self.load("validation.json")
        abstention_case = next(case for case in cases if not case["relevant_memory_ids"])
        self.assertNotEqual(pse_candidate_v2_rank(abstention_case), [])

    def test_lexical_copy_is_not_ranked_over_evidence(self) -> None:
        case = {
            "id": "generic-nonbenchmark-id",
            "memories": [
                {"id": "evidence", "text": "Backup key is stored in the steel drawer", "timestamp": "2026-01-01"},
                {"id": "echo", "text": "Where is the backup key stored?", "timestamp": "2026-07-01"},
            ],
            "query": "Where is the backup key stored?",
            "relevant_memory_ids": ["evidence"],
        }
        self.assertEqual(pse_candidate_v2_rank(case)[0], "evidence")


if __name__ == "__main__":
    unittest.main()
