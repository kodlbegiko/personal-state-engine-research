from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from personal_state_engine.external_trials import (
    ExternalTrialConfig,
    ExternalTrialError,
    bm25_sessions,
    build_request,
    execute_trial,
    write_immutable_trial,
)
from personal_state_engine.longmemeval import (
    LongMemEvalExample,
    LongMemEvalSession,
    LongMemEvalTurn,
)
from personal_state_engine.model_adapters import (
    ModelAdapterError,
    ModelResponse,
    RunManifest,
)


class SuccessfulAdapter:
    def complete(self, request):
        return ModelResponse(
            request_id=request.request_id,
            text="blue",
            usage={"input_tokens": 10, "output_tokens": 1},
            latency_ms=5.0,
            raw={"request_id": request.request_id, "text": "blue"},
        )


class FailingAdapter:
    def complete(self, request):
        raise ModelAdapterError("provider failed")


class ExternalTrialTests(unittest.TestCase):
    def manifest(self):
        return RunManifest(
            model_provider="test-provider",
            model_id="test-model",
            model_version="revision-1",
            temperature=0.0,
            seed=7,
            token_budget=64,
            timeout_seconds=2.0,
            tool_policy="none",
        )

    def example(self):
        return LongMemEvalExample(
            question_id="q1",
            question_type="multi-session",
            question="What is my favorite color?",
            answer="blue",
            question_date="2026-03-01",
            sessions=(
                LongMemEvalSession(
                    session_id="s1",
                    timestamp="2026-01-01",
                    turns=(
                        LongMemEvalTurn(
                            role="user",
                            content="My favorite color is blue.",
                        ),
                    ),
                ),
                LongMemEvalSession(
                    session_id="s2",
                    timestamp="2026-02-01",
                    turns=(
                        LongMemEvalTurn(
                            role="user",
                            content="I ordered pizza yesterday.",
                        ),
                    ),
                ),
            ),
            answer_session_ids=("s1",),
        )

    def config(self, baseline):
        return ExternalTrialConfig(
            run_id="run-1",
            dataset_name="LongMemEval-S",
            dataset_version="test-revision",
            dataset_sha256="dataset-sha256",
            split_name="development",
            split_manifest_sha256="split-sha256",
            baseline_id=baseline,
            baseline_version="external-baseline-v1",
            retrieval_item_limit=1,
            code_commit="commit-sha",
        )

    def test_b0_request_contains_no_cross_session_history(self):
        request, selected, reconstruction = build_request(
            self.example(),
            self.manifest(),
            self.config("EXT-B0"),
            request_id="request-1",
        )
        self.assertEqual(selected, ())
        self.assertEqual(reconstruction["selected_session_ids"], [])
        self.assertEqual(reconstruction["context_session_ids"], [])
        self.assertEqual(reconstruction["history_lexical_tokens"], 0)
        self.assertNotIn("favorite color is blue", request.messages[0]["content"])
        self.assertIn("What is my favorite color?", request.messages[0]["content"])

    def test_bm25_retrieves_relevant_session_deterministically(self):
        selected = bm25_sessions(
            self.example().question,
            self.example().sessions,
            k=1,
        )
        self.assertEqual([session.session_id for session in selected], ["s1"])

    def test_b5_history_budget_is_enforced_and_auditable(self):
        config = ExternalTrialConfig(
            run_id="run-budget",
            dataset_name="LongMemEval-S",
            dataset_version="test-revision",
            dataset_sha256="dataset-sha256",
            split_name="development",
            split_manifest_sha256="split-sha256",
            baseline_id="EXT-B5",
            baseline_version="external-baseline-v2",
            retrieval_item_limit=2,
            retrieval_token_budget=8,
            memory_token_budget=8,
            code_commit="commit-sha",
        )
        request, selected, reconstruction = build_request(
            self.example(),
            self.manifest(),
            config,
            request_id="request-budget",
        )
        self.assertEqual([session.session_id for session in selected], ["s1", "s2"])
        self.assertLessEqual(reconstruction["history_lexical_tokens"], 8)
        self.assertTrue(reconstruction["history_truncated"])
        self.assertEqual(
            reconstruction["truncation_policy"],
            "ranked-session concatenation with deterministic prefix truncation at lexical-token boundary",
        )
        self.assertIn("Conversation history:", request.messages[0]["content"])

    def test_completed_trial_preserves_attribution_and_accounting(self):
        times = iter((100.0, 100.01))
        record = execute_trial(
            self.example(),
            self.manifest(),
            self.config("EXT-B5"),
            SuccessfulAdapter(),
            trial_id="trial-1",
            request_id="request-1",
            now=times.__next__,
        )
        self.assertEqual(record.status, "completed")
        self.assertEqual(record.request_id, "request-1")
        self.assertEqual(record.model_revision, "revision-1")
        self.assertEqual(record.retrieved_items, ("s1",))
        self.assertGreater(record.retrieval_tokens, 0)
        self.assertEqual(record.total_tokens, 11)
        self.assertEqual(record.parsed_answer, "blue")

    def test_failed_trial_is_retained_as_error_record(self):
        times = iter((100.0, 100.01))
        record = execute_trial(
            self.example(),
            self.manifest(),
            self.config("EXT-B0"),
            FailingAdapter(),
            trial_id="trial-error",
            request_id="request-error",
            now=times.__next__,
        )
        self.assertEqual(record.status, "error")
        self.assertEqual(record.error_type, "ModelAdapterError")
        self.assertIsNone(record.parsed_answer)

    def test_immutable_trial_writer_rejects_collision(self):
        times = iter((100.0, 100.01))
        record = execute_trial(
            self.example(),
            self.manifest(),
            self.config("EXT-B0"),
            SuccessfulAdapter(),
            trial_id="trial-1",
            request_id="request-1",
            now=times.__next__,
        )
        with tempfile.TemporaryDirectory() as directory:
            output = write_immutable_trial(record, directory)
            payload = json.loads(Path(output).read_text(encoding="utf-8"))
            self.assertEqual(payload["trial_id"], "trial-1")
            with self.assertRaises(ExternalTrialError):
                write_immutable_trial(record, directory)


if __name__ == "__main__":
    unittest.main()
