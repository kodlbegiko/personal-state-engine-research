from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from personal_state_engine.benchmark_lock import (
    BenchmarkIntegrityError,
    create_lock,
    hash_file,
    load_scenarios,
    verify_lock,
    verify_lock_anchor,
    write_lock,
    write_lock_anchor,
)


class BenchmarkLockTests(unittest.TestCase):
    def scenario(self, scenario_id="x", split="pilot_test"):
        return {
            "id": scenario_id,
            "category": "c",
            "description": "d",
            "expected": "e",
            "split": split,
        }

    def create_fixture(self, directory: str, algorithm="sha256"):
        root = Path(directory)
        cases = root / "benchmarks/synthetic/scenarios.jsonl"
        baseline = root / "src/personal_state_engine/baselines.py"
        runner = root / "scripts/run_benchmark.py"
        cases.parent.mkdir(parents=True)
        baseline.parent.mkdir(parents=True)
        runner.parent.mkdir(parents=True)
        cases.write_text(json.dumps(self.scenario()) + "\n", encoding="utf-8")
        baseline.write_text("BASELINE = 1\n", encoding="utf-8")
        runner.write_text("print('run')\n", encoding="utf-8")
        paths = (
            "benchmarks/synthetic/scenarios.jsonl",
            "src/personal_state_engine/baselines.py",
            "scripts/run_benchmark.py",
        )
        lock = create_lock(
            paths,
            scenarios_path=paths[0],
            version="test",
            root=root,
            hash_algorithm=algorithm,
        )
        lock_path = write_lock(lock, root / "benchmarks/pilot/benchmark-lock.json")
        anchor = write_lock_anchor(
            lock_path, root / "benchmarks/pilot/benchmark-lock.sha256"
        )
        return root, paths, lock_path, anchor

    def test_loads_unique_split_scenarios(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.jsonl"
            path.write_text(json.dumps(self.scenario()) + "\n", encoding="utf-8")
            rows = load_scenarios(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], "x")

    def test_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.jsonl"
            row = self.scenario()
            path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n")
            with self.assertRaises(BenchmarkIntegrityError):
                load_scenarios(path)

    def test_sha256_and_git_blob_hashes_are_distinct_and_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "file.txt"
            path.write_text("content\n", encoding="utf-8")
            self.assertEqual(len(hash_file(path, "sha256")), 64)
            self.assertEqual(len(hash_file(path, "git_blob_sha1")), 40)
            self.assertNotEqual(
                hash_file(path, "sha256"), hash_file(path, "git_blob_sha1")
            )

    def test_lock_verifies_with_both_algorithms(self):
        for algorithm in ("sha256", "git_blob_sha1"):
            with self.subTest(algorithm=algorithm), tempfile.TemporaryDirectory() as directory:
                root, paths, lock_path, anchor = self.create_fixture(directory, algorithm)
                verify_lock_anchor(anchor, lock_path)
                self.assertEqual(
                    verify_lock(lock_path, root=root, expected_paths=paths).version,
                    "test",
                )

    def test_baseline_and_runner_tampering_are_detected(self):
        for target in (
            "src/personal_state_engine/baselines.py",
            "scripts/run_benchmark.py",
        ):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory:
                root, paths, lock_path, _ = self.create_fixture(
                    directory, "git_blob_sha1"
                )
                (root / target).write_text("tampered\n", encoding="utf-8")
                with self.assertRaisesRegex(BenchmarkIntegrityError, f"hash:{target}"):
                    verify_lock(lock_path, root=root, expected_paths=paths)

    def test_new_unlocked_execution_file_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root, paths, lock_path, _ = self.create_fixture(directory)
            unexpected = "scripts/new_runner.py"
            (root / unexpected).write_text("print('new')\n", encoding="utf-8")
            with self.assertRaisesRegex(BenchmarkIntegrityError, f"unlocked:{unexpected}"):
                verify_lock(
                    lock_path,
                    root=root,
                    expected_paths=(*paths, unexpected),
                )

    def test_anchor_detects_lock_rewrite(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, lock_path, anchor = self.create_fixture(directory)
            lock_path.write_text(lock_path.read_text() + " ", encoding="utf-8")
            with self.assertRaisesRegex(BenchmarkIntegrityError, "anchor hash mismatch"):
                verify_lock_anchor(anchor, lock_path)

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = root / "cases.jsonl"
            cases.write_text(json.dumps(self.scenario()) + "\n")
            with self.assertRaisesRegex(BenchmarkIntegrityError, "unsafe lock path"):
                create_lock(
                    ["../outside.py"],
                    scenarios_path="cases.jsonl",
                    version="test",
                    root=root,
                )

    def test_invalid_split_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.jsonl"
            path.write_text(json.dumps(self.scenario(split="final")) + "\n")
            with self.assertRaises(BenchmarkIntegrityError):
                load_scenarios(path)


if __name__ == "__main__":
    unittest.main()
