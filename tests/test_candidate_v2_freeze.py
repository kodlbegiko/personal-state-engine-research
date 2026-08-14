from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CandidateV2FreezeTests(unittest.TestCase):
    def test_frozen_source_and_protocol_hashes_match(self) -> None:
        freeze = json.loads((ROOT / "experiments/protocols/pse-candidate-v2-freeze.json").read_text(encoding="utf-8"))
        self.assertEqual(sha256(ROOT / freeze["source_path"]), freeze["source_sha256"])
        self.assertEqual(sha256(ROOT / freeze["preregistration_path"]), freeze["preregistration_sha256"])
        self.assertEqual(sha256(ROOT / "benchmarks/algorithm-development/adversarial-v3/development.json"), freeze["adversarial_development_sha256"])
        self.assertEqual(sha256(ROOT / "benchmarks/algorithm-development/adversarial-v3/validation.json"), freeze["adversarial_validation_sha256"])
        self.assertEqual(sha256(ROOT / "benchmarks/strong-baseline/synthetic-memory-cases-v1.json"), freeze["original_24_case_corpus_sha256"])
        self.assertFalse(freeze["sealed_final_accessed"])

    def test_withheld_was_created_after_source_freeze_and_is_fixed(self) -> None:
        manifest = json.loads((ROOT / "benchmarks/algorithm-development/adversarial-v3/withheld-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["candidate_freeze_commit"], "d627f61d0888306a97f3ef0b78aa29dc00c444bb")
        self.assertEqual(manifest["withheld_commit"], "fd73449462e6285a4e5aec095e0c84d565d83fbc")
        self.assertEqual(sha256(ROOT / "benchmarks/algorithm-development/adversarial-v3/withheld.json"), manifest["sha256"])
        self.assertFalse(manifest["independent_reproduction"])

    def test_candidate_source_contains_no_adversarial_case_ids(self) -> None:
        source = (ROOT / "src/personal_state_engine/candidate_v2.py").read_text(encoding="utf-8")
        self.assertNotIn("ADV3-DEV-", source)
        self.assertNotIn("ADV3-VAL-", source)
        self.assertNotIn("ADV3-HID-", source)
        self.assertNotIn("SB-SYN-", source)
        self.assertNotIn("relevant_memory_ids", source)


if __name__ == "__main__":
    unittest.main()
