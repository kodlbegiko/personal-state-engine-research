#!/usr/bin/env python3
from personal_state_engine.benchmark_lock import (
    pilot_lock_paths,
    verify_lock,
    verify_lock_anchor,
)


if __name__ == "__main__":
    lock_path = "benchmarks/pilot/benchmark-lock.json"
    anchor_path = "benchmarks/pilot/benchmark-lock.sha256"
    anchor = verify_lock_anchor(anchor_path, lock_path)
    lock = verify_lock(
        lock_path,
        expected_paths=pilot_lock_paths(),
    )
    print(
        f"verified {lock.version}: {lock.scenario_count} scenarios; "
        f"anchor sha256={anchor}"
    )
