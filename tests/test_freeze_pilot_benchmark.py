from __future__ import annotations

import unittest

from personal_state_engine.benchmark_lock import BenchmarkLock
from scripts.freeze_pilot_benchmark import (
    benchmark_inputs_changed,
    require_version_bump,
)


class FreezePilotBenchmarkTests(unittest.TestCase):
    def lock(self, *, version: str = "pilot-v0.4", digest: str = "a" * 40) -> BenchmarkLock:
        return BenchmarkLock(
            version=version,
            files={"scripts/run_benchmark.py": digest},
            scenario_count=1,
            split_counts={"pilot_test": 1},
            hash_algorithm="git_blob_sha1",
        )

    def test_unchanged_inputs_can_reuse_version(self):
        previous = self.lock()
        candidate = self.lock()
        self.assertFalse(benchmark_inputs_changed(previous, candidate))
        require_version_bump(previous, candidate)

    def test_changed_inputs_require_new_version(self):
        previous = self.lock()
        candidate = self.lock(digest="b" * 40)
        self.assertTrue(benchmark_inputs_changed(previous, candidate))
        with self.assertRaisesRegex(RuntimeError, "new benchmark version"):
            require_version_bump(previous, candidate)

    def test_changed_inputs_are_allowed_with_explicit_version_bump(self):
        previous = self.lock()
        candidate = self.lock(version="pilot-v0.5", digest="b" * 40)
        self.assertTrue(benchmark_inputs_changed(previous, candidate))
        require_version_bump(previous, candidate)


if __name__ == "__main__":
    unittest.main()
