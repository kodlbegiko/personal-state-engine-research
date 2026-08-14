from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from personal_state_engine.longmemeval_faithful_port import (
    EXPECTED_CASE_ID_SHA256,
    anonymous_response_id,
    build_blinded_inputs,
    build_faithful_port_prompt,
    build_official_prompt,
    case_ids_sha256,
    parse_strict_judgment,
    verify_archive_registry,
    verify_blinded_records,
)


class LongMemEvalFaithfulPortTests(unittest.TestCase):
    def test_official_prompt_routing(self) -> None:
        generic = build_official_prompt("multi-session", "Q", "A", "R", abstention=False)
        self.assertIn("Correct Answer: A", generic)
        temporal = build_official_prompt("temporal-reasoning", "Q", "A", "R", abstention=False)
        self.assertIn("off-by-one errors", temporal)
        update = build_official_prompt("knowledge-update", "Q", "A", "R", abstention=False)
        self.assertIn("updated answer", update)
        preference = build_official_prompt("single-session-preference", "Q", "A", "R", abstention=False)
        self.assertIn("Rubric: A", preference)
        abstention = build_official_prompt("single-session-user", "Q", "A", "R", abstention=True)
        self.assertIn("unanswerable question", abstention)

    def test_structured_suffix_does_not_replace_official_rubric(self) -> None:
        official = build_official_prompt("single-session-user", "Q", "A", "R", abstention=False)
        ported = build_faithful_port_prompt("single-session-user", "Q", "A", "R", abstention=False)
        self.assertTrue(ported.startswith(official))
        self.assertIn('{"label":"CORRECT"}', ported)

    def test_strict_parser_accepts_only_exact_schema(self) -> None:
        self.assertEqual(parse_strict_judgment('{"label":"CORRECT"}').status, "CORRECT")
        self.assertTrue(parse_strict_judgment('{"label":"CORRECT"}').correct)
        self.assertEqual(parse_strict_judgment('{"label":"INCORRECT"}').status, "INCORRECT")
        invalids = [
            "", "yes", "not yes", '{"label":"correct"}', '{"label":"CORRECT","extra":1}',
            '[{"label":"CORRECT"}]', '{"label":"CORRECT"} explanation',
            '{"label":"CORRECT","other":"INCORRECT"}',
        ]
        for value in invalids:
            with self.subTest(value=value):
                self.assertEqual(parse_strict_judgment(value).status, "INVALID")
                self.assertIsNone(parse_strict_judgment(value).correct)

    def test_operational_failures_are_invalid(self) -> None:
        self.assertEqual(parse_strict_judgment(None, timed_out=True).error, "timeout")
        self.assertEqual(parse_strict_judgment(None, truncated=True).error, "truncated_output")
        self.assertTrue(parse_strict_judgment(None, provider_error="rate_limit").error.startswith("provider_error:"))

    def test_case_hash_is_order_independent(self) -> None:
        case_ids = ["b", "a"]
        self.assertEqual(case_ids_sha256(case_ids), case_ids_sha256(reversed(case_ids)))
        self.assertNotEqual(case_ids_sha256(case_ids), EXPECTED_CASE_ID_SHA256)

    def test_anonymous_response_id_is_deterministic(self) -> None:
        self.assertEqual(anonymous_response_id("trial-1"), anonymous_response_id("trial-1"))
        self.assertNotEqual(anonymous_response_id("trial-1"), anonymous_response_id("trial-2"))
        self.assertNotIn("trial-1", anonymous_response_id("trial-1"))

    def test_blinding_omits_identity_fields_and_separates_key(self) -> None:
        split = {
            "records": [{"case_id": f"c{i:02d}", "is_abstention": False} for i in range(20)]
        }
        trials = []
        for index in range(20):
            for baseline in ("EXT-B0", "EXT-B5"):
                trials.append({
                    "trial_id": f"t-{index}-{baseline}",
                    "request_id": f"r-{index}-{baseline}",
                    "case_id": f"c{index:02d}",
                    "baseline_id": baseline,
                    "question_type": "single-session-user",
                    "reference_answer": "Kyoto",
                    "parsed_answer": "Kyoto",
                    "raw_prompt_or_reconstruction_fields": {"question": "Where?"},
                })
        blinded, key, leakage = build_blinded_inputs(trials, split)
        self.assertEqual(leakage, [])
        verify_blinded_records(blinded, key)
        self.assertEqual(len(blinded), 40)
        self.assertEqual(len(key), 40)
        self.assertFalse({"case_id", "baseline_id", "trial_id", "request_id"}.intersection(blinded[0]))
        self.assertIn("baseline_id", key[0])

    def test_answer_originated_identity_word_is_retained_and_declared(self) -> None:
        split = {"records": [{"case_id": f"c{i:02d}", "is_abstention": False} for i in range(20)]}
        trials = []
        for index in range(20):
            for baseline in ("EXT-B0", "EXT-B5"):
                trials.append({
                    "trial_id": f"t-{index}-{baseline}", "request_id": f"r-{index}-{baseline}",
                    "case_id": f"c{index:02d}", "baseline_id": baseline,
                    "question_type": "single-session-user", "reference_answer": "Use retrieval carefully",
                    "parsed_answer": "Use retrieval carefully",
                    "raw_prompt_or_reconstruction_fields": {"question": "What wording did I use?"},
                })
        blinded, key, leakage = build_blinded_inputs(trials, split)
        self.assertGreater(len(leakage), 0)
        verify_blinded_records(blinded, key, allowed_answer_originated_leakage=leakage)
        self.assertIn("retrieval", blinded[0]["model_response"].lower())

    def test_archive_registry_detects_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            import hashlib
            artifacts = []
            for index in range(59):
                payload = root / f"evidence-{index:02d}.json"
                payload.write_text("{}\n", encoding="utf-8")
                digest = hashlib.sha256(payload.read_bytes()).hexdigest()
                artifacts.append({"path": payload.name, "sha256": digest, "size_bytes": payload.stat().st_size})
            registry = {"artifact_count": 59, "artifacts": artifacts}
            (root / "archive-registry.json").write_text(json.dumps(registry), encoding="utf-8")
            self.assertEqual(verify_archive_registry(root)["status"], "PASS")
            payload = root / "evidence-00.json"
            payload.write_text('{"changed":true}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_archive_registry(root)


if __name__ == "__main__":
    unittest.main()
