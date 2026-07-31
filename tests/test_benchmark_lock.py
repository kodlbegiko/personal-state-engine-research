from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from personal_state_engine.benchmark_lock import (
    BenchmarkIntegrityError,
    create_lock,
    load_scenarios,
    verify_lock,
    write_lock,
)


class BenchmarkLockTests(unittest.TestCase):
    def test_loads_unique_split_scenarios(self):
        rows = load_scenarios("benchmarks/synthetic/scenarios.jsonl")
        self.assertEqual(len(rows), 9)
        self.assertEqual(len({row["id"] for row in rows}), 9)

    def test_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.jsonl"
            row = {"id": "x", "category": "c", "description": "d", "expected": "e", "split": "development"}
            path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n")
            with self.assertRaises(BenchmarkIntegrityError):
                load_scenarios(path)

    def test_lock_verifies_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = root / "cases.jsonl"
            cases.write_text(
                json.dumps({"id": "x", "category": "c", "description": "d", "expected": "e", "split": "pilot_test"}) + "\n"
            )
            lock = create_lock([cases], scenarios_path=cases, version="test")
            # Convert the absolute key to a root-relative key for a portable lock.
            portable = type(lock)(lock.version, {"cases.jsonl": next(iter(lock.files.values()))}, lock.scenario_count, lock.split_counts)
            lock_path = write_lock(portable, root / "lock.json")
            self.assertEqual(verify_lock(lock_path, root=root).version, "test")
            cases.write_text(cases.read_text() + " ")
            with self.assertRaises(BenchmarkIntegrityError):
                verify_lock(lock_path, root=root)

    def test_invalid_split_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.jsonl"
            path.write_text(json.dumps({"id": "x", "category": "c", "description": "d", "expected": "e", "split": "final"}) + "\n")
            with self.assertRaises(BenchmarkIntegrityError):
                load_scenarios(path)


if __name__ == "__main__":
    unittest.main()
