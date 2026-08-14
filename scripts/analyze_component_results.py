#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from personal_state_engine.scoring import paired_mcnemar, summarise_binary


def analyze(
    raw_path: str = "results/raw/component_benchmark.jsonl",
    output_path: str = "results/processed/component_benchmark_statistics.json",
):
    rows = [json.loads(line) for line in Path(raw_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    by_baseline: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_baseline.setdefault(row["baseline"], []).append(row)

    summaries: dict[str, dict[str, object]] = {}
    paired: dict[str, dict[str, object]] = {}
    base = {row["scenario"]: bool(row["passed"]) for row in by_baseline["B0"]}
    for baseline, baseline_rows in sorted(by_baseline.items()):
        summary = summarise_binary(bool(row["passed"]) for row in baseline_rows)
        summaries[baseline] = {
            "n": summary.n,
            "successes": summary.successes,
            "rate": round(summary.rate, 6),
            "wilson_95": [round(summary.lower_95, 6), round(summary.upper_95, 6)],
        }
        if baseline != "B0":
            current = {row["scenario"]: bool(row["passed"]) for row in baseline_rows}
            comparison = paired_mcnemar(base, current)
            paired[f"B0_vs_{baseline}"] = {
                "pairs": comparison.pairs,
                "b0_only": comparison.left_only,
                "other_only": comparison.right_only,
                "difference": round(comparison.difference, 6),
                "exact_mcnemar_p": round(comparison.exact_p_value, 6),
            }

    report = {
        "interpretation": "descriptive_architecture_sensitive_not_model_efficacy",
        "warning": (
            "Intervals and exact paired tests describe this fixed nine-case component set only. "
            "They are not population estimates and must not be used as evidence of real-model superiority."
        ),
        "baseline_summaries": summaries,
        "paired_against_B0": paired,
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination, report


if __name__ == "__main__":
    path, _ = analyze()
    print(path)
