from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DevelopmentMatrixProtocolTests(unittest.TestCase):
    def test_protocol_and_frozen_manifest_are_consistent(self) -> None:
        protocol = json.loads(
            (ROOT / "experiments/protocols/longmemeval-development-matrix-v1.json").read_text(encoding="utf-8")
        )
        manifest = json.loads(
            (ROOT / "experiments/splits/longmemeval-development-matrix-v1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(protocol["target_case_count"], 20)
        self.assertEqual(manifest["sample_count"], 20)
        self.assertEqual(len(manifest["case_ids"]), 20)
        self.assertEqual(len(set(manifest["case_ids"])), 20)
        self.assertEqual(manifest["abstention_case_count"], 4)
        self.assertFalse(manifest["sealed_final_accessed"])
        self.assertEqual(manifest["history_isolation"], "PASS")
        self.assertEqual(
            manifest["question_type_distribution"],
            protocol["selection"]["question_type_targets"],
        )
        without_self = dict(manifest)
        recorded_hash = without_self.pop("manifest_sha256")
        freezer = load_script("freeze_longmemeval_development_matrix.py")
        self.assertEqual(recorded_hash, freezer.canonical_sha256(without_self))

    def test_model_and_tokenizer_revisions_are_exact(self) -> None:
        model = json.loads(
            (ROOT / "experiments/models/qwen2.5-0.5b-instruct-transformersjs.json").read_text(encoding="utf-8")
        )
        runner = load_script("run_longmemeval_development_matrix.py")
        self.assertEqual(
            runner.require_exact_revision(model["model_revision"], field="model_revision"),
            model["model_revision"],
        )
        self.assertEqual(
            runner.require_exact_revision(model["tokenizer_revision"], field="tokenizer_revision"),
            model["tokenizer_revision"],
        )
        for floating in ("main", "latest", "stable", "956050e"):
            with self.assertRaises(runner.DevelopmentMatrixError):
                runner.require_exact_revision(floating, field="model_revision")

    def test_semantic_judge_parser_retains_invalid_output(self) -> None:
        runner = load_script("run_longmemeval_development_matrix.py")
        valid = runner.parse_judge_output('{"correct": true, "rationale": "Equivalent answer."}')
        self.assertEqual(valid["status"], "VALID")
        self.assertEqual(valid["score"], 1)
        invalid = runner.parse_judge_output("correct")
        self.assertEqual(invalid["status"], "INVALID")
        self.assertIsNone(invalid["score"])
        self.assertIn("raw_text", invalid)

    def test_protocol_forbids_reference_driven_selection(self) -> None:
        protocol = json.loads(
            (ROOT / "experiments/protocols/longmemeval-development-matrix-v1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            set(protocol["selection"]["forbidden_fields"]),
            {"answer", "reference_answer", "has_answer"},
        )
        self.assertEqual(protocol["forbidden_split"], "sealed-final")


if __name__ == "__main__":
    unittest.main()
