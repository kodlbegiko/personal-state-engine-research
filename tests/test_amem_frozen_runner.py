from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_amem_frozen_synthetic.py"
CORPUS = ROOT / "benchmarks/strong-baseline/synthetic-memory-cases-v1.json"

spec = importlib.util.spec_from_file_location("amem_frozen_runner", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class AMemFrozenRunnerTests(unittest.TestCase):
    def test_frozen_corpus_hash_is_exact(self) -> None:
        self.assertEqual(module.sha256_file(CORPUS), module.EXPECTED_CORPUS_SHA256)

    def test_six_shards_partition_all_cases_exactly_once(self) -> None:
        cases = json.loads(CORPUS.read_text(encoding="utf-8"))["cases"]
        selected = []
        for index in range(6):
            selected.extend(case["id"] for case in module.select_cases(cases, index, 6))
        self.assertEqual(len(selected), 24)
        self.assertEqual(len(set(selected)), 24)
        self.assertEqual(set(selected), {case["id"] for case in cases})

    def test_invalid_shards_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            module.select_cases([], 0, 0)
        with self.assertRaises(ValueError):
            module.select_cases([], 6, 6)


if __name__ == "__main__":
    unittest.main()
