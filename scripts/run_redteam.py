#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from personal_state_engine.models import MemoryKind, MemoryRecord, Provenance, SourceType
from personal_state_engine.policy import MemoryWritePolicy


def run(corpus: str = "benchmarks/redteam/memory-write-policy.jsonl", output_dir: str = "results"):
    policy = MemoryWritePolicy()
    observations: list[dict[str, object]] = []
    for line in Path(corpus).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        record = MemoryRecord(
            user_id="redteam-user",
            kind=MemoryKind.SEMANTIC,
            key="candidate_memory",
            content=case["content"],
            provenance=Provenance(SourceType.USER_CONFIRMED, case["id"], user_confirmed=True),
        )
        decision = policy.evaluate(record)
        observed_allowed = decision.allowed
        observations.append(
            {
                "id": case["id"],
                "category": case["category"],
                "expected_allowed": case["expected_allowed"],
                "observed_allowed": observed_allowed,
                "passed": observed_allowed == case["expected_allowed"],
                "reasons": list(decision.reasons),
            }
        )

    positives = [row for row in observations if row["expected_allowed"] is False]
    negatives = [row for row in observations if row["expected_allowed"] is True]
    true_positive = sum(row["observed_allowed"] is False for row in positives)
    false_negative = len(positives) - true_positive
    true_negative = sum(row["observed_allowed"] is True for row in negatives)
    false_positive = len(negatives) - true_negative
    summary = {
        "cases": len(observations),
        "passed": sum(bool(row["passed"]) for row in observations),
        "true_positive": true_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "injection_or_secret_recall": round(true_positive / len(positives), 4) if positives else None,
        "benign_acceptance_rate": round(true_negative / len(negatives), 4) if negatives else None,
    }
    output = Path(output_dir)
    raw = output / "raw" / "memory_write_redteam.jsonl"
    processed = output / "processed" / "memory_write_redteam_summary.json"
    raw.parent.mkdir(parents=True, exist_ok=True)
    processed.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("\n".join(json.dumps(row, sort_keys=True, ensure_ascii=False) for row in observations) + "\n", encoding="utf-8")
    processed.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return raw, processed, summary


if __name__ == "__main__":
    raw, processed, summary = run()
    print(f"raw={raw}")
    print(f"summary={processed}")
    print(json.dumps(summary, sort_keys=True))
