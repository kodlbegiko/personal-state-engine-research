from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from personal_state_engine.longmemeval_evaluator import (
    build_official_prompt,
    calculate_calibration,
    cohen_kappa,
    deterministic_case_mapping,
    exact_mcnemar_p,
    load_trials,
    parse_strict_yes_no,
    prompt_templates_sha256,
    summarize_formal_results,
)


class LongMemEvalEvaluatorV2Tests(unittest.TestCase):
    def test_prompt_templates_are_pinned(self) -> None:
        self.assertEqual(
            prompt_templates_sha256(),
            "be177cbb0e82bf279ad8c24e8d553ef80222464dd51c39ef7bea7231623d28e6",
        )

    def test_official_prompt_routes_question_types(self) -> None:
        temporal = build_official_prompt(
            "temporal-reasoning", "How many days?", "18 days", "19 days", abstention=False
        )
        self.assertIn("do not penalize off-by-one errors", temporal)
        preference = build_official_prompt(
            "single-session-preference", "Suggest food", "Vegetarian", "Salad", abstention=False
        )
        self.assertIn("Rubric:", preference)
        abstention = build_official_prompt(
            "single-session-user", "What is the secret?", "Unknown", "I do not know", abstention=True
        )
        self.assertIn("unanswerable question", abstention)

    def test_strict_parser_accepts_only_enum(self) -> None:
        self.assertTrue(parse_strict_yes_no("YES").correct)
        self.assertFalse(parse_strict_yes_no("no.").correct)
        self.assertEqual(parse_strict_yes_no("yes because it matches").status, "INVALID")
        self.assertEqual(parse_strict_yes_no('{"answer":"yes"}').status, "INVALID")

    def test_blinding_is_deterministic_and_balanced_per_case(self) -> None:
        first = deterministic_case_mapping("case-1", 17)
        second = deterministic_case_mapping("case-1", 17)
        self.assertEqual(first, second)
        self.assertEqual(set(first.values()), {"EXT-B0", "EXT-B5"})

    def test_cohen_kappa(self) -> None:
        self.assertEqual(cohen_kappa([True, False], [True, False]), 1.0)
        self.assertAlmostEqual(cohen_kappa([True, True, False, False], [True, False, True, False]), 0.0)

    def test_calibration_passes_only_all_fixed_thresholds(self) -> None:
        audit_rows = [
            {"case_id": "c1", "baseline_id": "EXT-B0", "human_decision": True, "is_abstention": False},
            {"case_id": "c1", "baseline_id": "EXT-B5", "human_decision": False, "is_abstention": False},
            {"case_id": "c2", "baseline_id": "EXT-B0", "human_decision": True, "is_abstention": True},
            {"case_id": "c2", "baseline_id": "EXT-B5", "human_decision": False, "is_abstention": True},
        ]
        judgments = {
            (row["case_id"], row["baseline_id"]): {
                "status": "VALID",
                "correct": row["human_decision"],
            }
            for row in audit_rows
        }
        report = calculate_calibration(
            audit_rows,
            judgments,
            full_output_count=40,
            full_invalid_count=0,
            thresholds={
                "raw_agreement_minimum": 0.8,
                "cohen_kappa_minimum": 0.6,
                "invalid_output_rate_maximum": 0.05,
            },
            blinding_verified=True,
            old_evidence_preserved=True,
            raw_outputs_preserved=True,
        )
        self.assertEqual(report["calibration_verdict"], "PASS")
        judgments[("c1", "EXT-B5")] = {"status": "VALID", "correct": True}
        failed = calculate_calibration(
            audit_rows,
            judgments,
            full_output_count=40,
            full_invalid_count=3,
            thresholds={
                "raw_agreement_minimum": 0.8,
                "cohen_kappa_minimum": 0.6,
                "invalid_output_rate_maximum": 0.05,
            },
            blinding_verified=True,
            old_evidence_preserved=True,
            raw_outputs_preserved=True,
        )
        self.assertEqual(failed["calibration_verdict"], "FAIL")
        self.assertEqual(failed["use_for_formal_correctness"], "PROHIBITED")

    def test_exact_mcnemar(self) -> None:
        self.assertIsNone(exact_mcnemar_p(0, 0))
        self.assertAlmostEqual(exact_mcnemar_p(4, 0), 0.125)

    def test_load_trials_enforces_fixed_matrix_and_b0_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(20):
                for baseline in ("EXT-B0", "EXT-B5"):
                    row = {
                        "case_id": f"case-{index:02d}",
                        "baseline_id": baseline,
                        "trial_id": f"trial-{index}-{baseline}",
                        "request_id": f"request-{index}-{baseline}",
                        "retrieved_items": [] if baseline == "EXT-B0" else [{"session_id": "s1"}],
                        "retrieval_tokens": 0 if baseline == "EXT-B0" else 10,
                        "raw_prompt_or_reconstruction_fields": {"history": "" if baseline == "EXT-B0" else "history"},
                    }
                    (root / f"{index:02d}-{baseline}.json").write_text(json.dumps(row), encoding="utf-8")
            loaded = load_trials(root)
            self.assertEqual(len(loaded), 40)

    def test_formal_summary_is_paired_and_cost_ratio_is_undefined_without_gain(self) -> None:
        trials = []
        judgments = []
        for index in range(20):
            for baseline in ("EXT-B0", "EXT-B5"):
                trials.append(
                    {
                        "case_id": f"c{index}",
                        "baseline_id": baseline,
                        "input_tokens": 10 if baseline == "EXT-B0" else 20,
                        "output_tokens": 2,
                        "total_tokens": 12 if baseline == "EXT-B0" else 22,
                        "latency_ms": 100 if baseline == "EXT-B0" else 200,
                        "storage_bytes": 50 if baseline == "EXT-B0" else 80,
                        "estimated_cost": 0.0,
                    }
                )
                judgments.append(
                    {
                        "case_id": f"c{index}",
                        "baseline_id": baseline,
                        "status": "VALID",
                        "correct": index < 5,
                    }
                )
        summary = summarize_formal_results(trials, judgments)
        self.assertEqual(summary["paired"]["b5_wins"], 0)
        self.assertEqual(summary["paired"]["b5_losses"], 0)
        self.assertEqual(
            summary["resource_comparison"]["cost_per_additional_correct_answer_display"],
            "UNDEFINED",
        )


if __name__ == "__main__":
    unittest.main()
