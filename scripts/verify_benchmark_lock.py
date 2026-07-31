#!/usr/bin/env python3
from personal_state_engine.benchmark_lock import verify_lock


if __name__ == "__main__":
    lock = verify_lock("benchmarks/pilot/benchmark-lock.json")
    print(f"verified {lock.version}: {lock.scenario_count} scenarios")
