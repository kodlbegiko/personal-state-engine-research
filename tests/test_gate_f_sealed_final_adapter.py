from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_gate_f_sealed_final.py"
spec = importlib.util.spec_from_file_location("gate_f_eval", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class GateFAdapterTests(unittest.TestCase):
    def row(self, qid: str = "q1"):
        return {
            "question_id": qid,
            "question_type": "knowledge-update",
            "question": "What is the current preference?",
            "answer": "synthetic-only",
            "question_date": "2026-01-03",
            "haystack_session_ids": ["s1", "s2"],
            "haystack_dates": ["2026-01-01", "2026-01-02"],
            "haystack_sessions": [
                [
                    {"role": "user", "content": "Synthetic old state."},
                    {"role": "assistant", "content": "Synthetic acknowledgement."},
                ],
                [
                    {"role": "user", "content": "Synthetic current state.", "has_answer": True},
                    {"role": "assistant", "content": "Synthetic acknowledgement."},
                ],
            ],
            "answer_session_ids": ["s2"],
        }

    def test_answerable_maps_has_answer_to_relevant_memory(self):
        case = module.adapt_row(self.row())
        self.assertEqual(case["id"], "q1")
        self.assertEqual(len(case["memories"]), 4)
        self.assertEqual(case["relevant_memory_ids"], ["q1::s1::t0"])
        self.assertFalse(case["official_abstention"])

    def test_abs_suffix_forces_official_abstention(self):
        case = module.adapt_row(self.row("q1_abs"))
        self.assertEqual(case["relevant_memory_ids"], [])
        self.assertTrue(case["official_abstention"])

    def test_misaligned_sessions_fail_closed(self):
        row = self.row()
        row["haystack_dates"] = ["2026-01-01"]
        with self.assertRaisesRegex(ValueError, "must align"):
            module.adapt_row(row)

    def test_answerable_without_evidence_fails_closed(self):
        row = self.row()
        row["haystack_sessions"][1][0].pop("has_answer")
        with self.assertRaisesRegex(ValueError, "no has_answer evidence"):
            module.adapt_row(row)

    def test_metrics_use_fractional_recall_for_multiple_evidence_turns(self):
        case = {
            "id": "q",
            "category": "synthetic",
            "query": "q",
            "memories": [{"id": "a", "text": "a"}, {"id": "b", "text": "b"}, {"id": "c", "text": "c"}],
            "relevant_memory_ids": ["a", "b"],
        }
        ranker = lambda _case, _k: ["a", "c"]
        metrics, rows = module.evaluate_ranker([case], ranker)
        self.assertEqual(rows["q"]["rr"], 1.0)
        self.assertEqual(metrics["R@1"], 0.5)
        self.assertEqual(metrics["R@3"], 0.5)
        self.assertEqual(metrics["answerable_recall"], 1.0)


if __name__ == "__main__":
    unittest.main()
