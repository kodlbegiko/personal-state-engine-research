from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from personal_state_engine.longmemeval import (
    LongMemEvalFormatError,
    LongMemEvalHypothesis,
    iter_history_turns,
    load_hypotheses,
    load_longmemeval,
    render_history_json,
    write_hypotheses,
)


class LongMemEvalAdapterTests(unittest.TestCase):
    def row(self):
        return {
            "question_id": "q1",
            "question_type": "knowledge-update",
            "question": "What is the current preference?",
            "answer": "tea",
            "question_date": "2026-01-03",
            "haystack_session_ids": ["s1", "s2"],
            "haystack_dates": ["2026-01-01", "2026-01-02"],
            "haystack_sessions": [
                [
                    {"role": "user", "content": "I like coffee."},
                    {"role": "assistant", "content": "Noted."},
                ],
                [
                    {
                        "role": "user",
                        "content": "I now prefer tea.",
                        "has_answer": True,
                    },
                    {"role": "assistant", "content": "Updated."},
                ],
            ],
            "answer_session_ids": ["s2"],
        }

    def write_dataset(self, directory, rows):
        path = Path(directory) / "dataset.json"
        path.write_text(json.dumps(rows), encoding="utf-8")
        return path

    def test_loads_official_shape_and_preserves_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            examples = load_longmemeval(
                self.write_dataset(directory, [self.row()])
            )
            self.assertEqual(len(examples), 1)
            example = examples[0]
            self.assertEqual(example.answer_session_ids, ("s2",))
            self.assertTrue(example.sessions[1].turns[0].has_answer)
            self.assertFalse(example.is_abstention)

    def test_duplicate_question_id_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            row = self.row()
            with self.assertRaisesRegex(
                LongMemEvalFormatError, "duplicate question_id"
            ):
                load_longmemeval(self.write_dataset(directory, [row, row]))

    def test_session_arrays_must_align(self):
        with tempfile.TemporaryDirectory() as directory:
            row = self.row()
            row["haystack_dates"] = ["2026-01-01"]
            with self.assertRaisesRegex(LongMemEvalFormatError, "must align"):
                load_longmemeval(self.write_dataset(directory, [row]))

    def test_invalid_turn_role_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            row = self.row()
            row["haystack_sessions"][0][0]["role"] = "system"
            with self.assertRaisesRegex(
                LongMemEvalFormatError, "user or assistant"
            ):
                load_longmemeval(self.write_dataset(directory, [row]))

    def test_answer_session_must_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            row = self.row()
            row["answer_session_ids"] = ["missing"]
            with self.assertRaisesRegex(
                LongMemEvalFormatError, "absent from history"
            ):
                load_longmemeval(self.write_dataset(directory, [row]))

    def test_rendering_supports_recent_sessions_and_user_only(self):
        with tempfile.TemporaryDirectory() as directory:
            example = load_longmemeval(
                self.write_dataset(directory, [self.row()])
            )[0]
            rendered = json.loads(
                render_history_json(
                    example,
                    include_assistant=False,
                    max_sessions=1,
                )
            )
            self.assertEqual([item["session_id"] for item in rendered], ["s2"])
            self.assertEqual(
                [message["role"] for message in rendered[0]["messages"]],
                ["user"],
            )
            turns = list(iter_history_turns(example, include_assistant=False))
            self.assertEqual(len(turns), 2)

    def test_hypothesis_jsonl_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hypotheses.jsonl"
            write_hypotheses(
                [LongMemEvalHypothesis("q1", "tea")],
                path,
            )
            loaded = load_hypotheses(path)
            self.assertEqual(
                loaded,
                (LongMemEvalHypothesis("q1", "tea"),),
            )


if __name__ == "__main__":
    unittest.main()
