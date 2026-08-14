from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from personal_state_engine.abstention_gate_v1 import SIMILARITY_THRESHOLD, abstention_gate_v1_rank
from personal_state_engine.candidate_v2 import pse_candidate_v2_rank

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks/algorithm-development/abstention-dev-v1"
RESULT = ROOT / "results/abstention-gate-v1/results.json"


def load(name: str) -> list[dict]:
    return json.loads((BENCH / name).read_text(encoding="utf-8"))["cases"]


def score(cases: list[dict], ranker) -> dict:
    answerable = [case for case in cases if case["relevant_memory_ids"]]
    no_evidence = [case for case in cases if not case["relevant_memory_ids"]]
    false_abs, false_ret = [], []
    top1 = top5 = 0
    for case in answerable:
        ranking = ranker(case, 5)
        relevant = set(case["relevant_memory_ids"])
        if not ranking:
            false_abs.append(case["id"])
        top1 += bool(ranking and ranking[0] in relevant)
        top5 += bool(relevant & set(ranking[:5]))
    for case in no_evidence:
        if ranker(case, 5):
            false_ret.append(case["id"])
    return {
        "answerable_cases": len(answerable),
        "no_evidence_cases": len(no_evidence),
        "abstention_accuracy": 1 - len(false_ret) / len(no_evidence),
        "false_retrieval_rate": len(false_ret) / len(no_evidence),
        "false_abstention_rate": len(false_abs) / len(answerable),
        "answerable_recall@1": top1 / len(answerable),
        "answerable_recall@5": top5 / len(answerable),
        "false_retrieval_ids": false_ret,
        "false_abstention_ids": false_abs,
    }


class AbstentionGateV1Tests(unittest.TestCase):
    def test_frozen_hashes_and_threshold(self) -> None:
        freeze = json.loads((BENCH / "freeze-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256((BENCH / "development.json").read_bytes()).hexdigest(), freeze["development"]["sha256"])
        self.assertEqual(hashlib.sha256((BENCH / "validation.json").read_bytes()).hexdigest(), freeze["validation"]["sha256"])
        held = json.loads((BENCH / "withheld-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256((BENCH / "withheld.json").read_bytes()).hexdigest(), held["sha256"])
        self.assertEqual(SIMILARITY_THRESHOLD, 0.22)
        self.assertFalse(held["sealed_final_accessed"])

    def test_committed_results_reconstruct(self) -> None:
        expected = json.loads(RESULT.read_text(encoding="utf-8"))
        systems = {"always_retrieve": pse_candidate_v2_rank, "abstention_gate_v1": abstention_gate_v1_rank}
        for split in ("development", "validation", "withheld"):
            cases = load(f"{split}.json")
            for name, ranker in systems.items():
                self.assertEqual(score(cases, ranker), expected["splits"][split][name])

    def test_clean_withheld_improves_abstention_without_recall_loss(self) -> None:
        result = json.loads(RESULT.read_text(encoding="utf-8"))
        held = result["splits"]["withheld"]
        gate = held["abstention_gate_v1"]
        always = held["always_retrieve"]
        self.assertGreater(gate["abstention_accuracy"], always["abstention_accuracy"])
        self.assertEqual(gate["answerable_recall@1"], 1.0)
        self.assertEqual(gate["answerable_recall@5"], 1.0)
        self.assertEqual(gate["false_abstention_rate"], 0.0)
        self.assertFalse(result["tuning_after_withheld"])
        self.assertFalse(result["sealed_final_accessed"])


if __name__ == "__main__":
    unittest.main()
