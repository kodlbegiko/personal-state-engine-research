#!/usr/bin/env python3
from personal_state_engine.benchmark_lock import (
    create_lock,
    pilot_lock_paths,
    write_lock,
    write_lock_anchor,
)


if __name__ == "__main__":
    lock_path = "benchmarks/pilot/benchmark-lock.json"
    lock = create_lock(
        pilot_lock_paths(),
        scenarios_path="benchmarks/synthetic/scenarios.jsonl",
        version="pilot-v0.4",
        hash_algorithm="git_blob_sha1",
    )
    output = write_lock(lock, lock_path)
    anchor = write_lock_anchor(output, "benchmarks/pilot/benchmark-lock.sha256")
    print(output)
    print(anchor)
