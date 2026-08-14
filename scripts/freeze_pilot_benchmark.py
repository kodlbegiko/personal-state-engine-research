#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from personal_state_engine.benchmark_lock import (
    BenchmarkLock,
    create_lock,
    load_lock,
    pilot_lock_paths,
    write_lock,
    write_lock_anchor,
)


def benchmark_inputs_changed(previous: BenchmarkLock, candidate: BenchmarkLock) -> bool:
    return (
        previous.files != candidate.files
        or previous.scenario_count != candidate.scenario_count
        or previous.split_counts != candidate.split_counts
        or previous.hash_algorithm != candidate.hash_algorithm
    )


def require_version_bump(previous: BenchmarkLock, candidate: BenchmarkLock) -> None:
    if benchmark_inputs_changed(previous, candidate) and previous.version == candidate.version:
        raise RuntimeError(
            "benchmark-affecting inputs changed; pass --version with a new benchmark version"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version",
        help=(
            "Benchmark version to write. If omitted, reuse the current lock version only "
            "when benchmark-affecting inputs are unchanged."
        ),
    )
    args = parser.parse_args()

    lock_path = Path("benchmarks/pilot/benchmark-lock.json")
    existing = load_lock(lock_path) if lock_path.is_file() else None
    if existing is None and not args.version:
        raise RuntimeError("--version is required when creating the first benchmark lock")

    version = args.version or existing.version
    candidate = create_lock(
        pilot_lock_paths(),
        scenarios_path="benchmarks/synthetic/scenarios.jsonl",
        version=version,
        hash_algorithm="git_blob_sha1",
    )
    if existing is not None:
        require_version_bump(existing, candidate)

    output = write_lock(candidate, lock_path)
    anchor = write_lock_anchor(output, "benchmarks/pilot/benchmark-lock.sha256")
    print(output)
    print(anchor)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
