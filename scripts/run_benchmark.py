#!/usr/bin/env python3
from personal_state_engine.evaluation import write_results


if __name__ == "__main__":
    raw, summary = write_results("results")
    print(f"raw={raw}")
    print(f"summary={summary}")
