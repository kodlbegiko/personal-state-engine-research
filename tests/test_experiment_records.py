from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from personal_state_engine.experiment_records import (
    TrialRecord,
    TrialRecordError,
    read_trials,
    write_trials,
)


class TrialRecordTests(unittest.TestCase):
    def record(self, **overrides):
        data = {
            "trial_id": "B7-case-0",
            "baseline": "B7",
            "scenario_id": "case",
            "split": "validation",
            "model_provider": "provider",
            "model_id": "model",
            "model_version": "2026-07-31",
            "seed": 7,
            "repetition": 0,
            "status": "completed",
            "passed": True,
            "latency_ms": 12.5,
            "input_tokens": 100,
            "output_tokens": 20,
            "estimated_cost_usd": 0.001,
            "output_text": "ok",
        }
        data.update(overrides)
        return TrialRecord(**data)

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trials.jsonl"
            write_trials([self.record()], path)
            self.assertEqual(read_trials(path), [self.record()])

    def test_duplicate_trial_id_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(TrialRecordError):
                write_trials([self.record(), self.record()], Path(directory) / "trials.jsonl")

    def test_placeholder_version_rejected(self):
        with self.assertRaises(TrialRecordError):
            self.record(model_version="PIN_EXACT_VERSION").validate()

    def test_completed_trial_requires_score(self):
        with self.assertRaises(TrialRecordError):
            self.record(passed=None).validate()

    def test_error_trial_may_have_no_score(self):
        self.record(status="error", passed=None, error_type="provider_error").validate()


if __name__ == "__main__":
    unittest.main()
