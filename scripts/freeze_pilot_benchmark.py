#!/usr/bin/env python3
from personal_state_engine.benchmark_lock import create_lock, write_lock


if __name__ == "__main__":
    lock = create_lock(
        [
            "benchmarks/synthetic/scenarios.jsonl",
            "src/personal_state_engine/evaluation.py",
            "benchmarks/redteam/memory-write-policy.jsonl",
            "src/personal_state_engine/policy.py",
            "src/personal_state_engine/scoring.py",
            "scripts/run_redteam.py",
            "scripts/analyze_component_results.py",
        ],
        scenarios_path="benchmarks/synthetic/scenarios.jsonl",
        version="pilot-v0.3",
    )
    output = write_lock(lock, "benchmarks/pilot/benchmark-lock.json")
    print(output)
