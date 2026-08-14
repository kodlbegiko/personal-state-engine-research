from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from personal_state_engine.longmemeval import load_longmemeval


class LongMemEvalCleanedCompatibilityTests(unittest.TestCase):
    def test_duplicate_source_session_ids_are_preserved(self):
        row = {
            "question_id": "q1",
            "question_type": "multi-session",
            "question": "What happened?",
            "answer": "second",
            "question_date": "2026-01-03",
            "haystack_session_ids": ["duplicate", "duplicate"],
            "haystack_dates": ["2026-01-01", "2026-01-02"],
            "haystack_sessions": [
                [{"role": "user", "content": "first"}],
                [
                    {
                        "role": "user",
                        "content": "second",
                        "has_answer": True
                    }
                ]
            ],
            "answer_session_ids": ["duplicate"]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.json"
            path.write_text(json.dumps([row]), encoding="utf-8")
            example = load_longmemeval(path)[0]
        self.assertEqual(
            [session.session_id for session in example.sessions],
            ["duplicate", "duplicate"]
        )
        self.assertEqual(
            [session.timestamp for session in example.sessions],
            ["2026-01-01", "2026-01-02"]
        )
        self.assertTrue(example.sessions[1].turns[0].has_answer)


if __name__ == "__main__":
    unittest.main()
