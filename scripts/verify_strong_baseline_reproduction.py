#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_VERDICTS = {
    "BLOCKED BY SOURCE AVAILABILITY",
    "BLOCKED BY LICENSE",
    "BLOCKED BY COMPUTE",
    "BLOCKED BY ZERO-COST CONSTRAINT",
    "BLOCKED BY IMPLEMENTATION FAILURE",
    "RETRIEVAL-LEVEL REPRODUCTION COMPLETE",
    "REDUCED STRONG-BASELINE PILOT COMPLETE",
    "STRONG BASELINE DEVELOPMENT REPRODUCTION COMPLETE",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    selection = json.loads((ROOT / "experiments/baselines/strong-baseline-selection-v1.json").read_text())
    assert selection["selection_frozen_before_results"] is True
    assert selection["selected_without_pse_result_visibility"] is True
    assert selection["primary_baseline"] == "A-MEM"

    source = json.loads((ROOT / "references/strong-baseline-primary-source.json").read_text())
    assert source["commit_sha"] == "0c8039f28fdcc08189a23c07a3437d9d2482f9c2"
    assert source["license"] == "MIT"

    corpus = ROOT / "benchmarks/strong-baseline/synthetic-memory-cases-v1.json"
    expected = (ROOT / "benchmarks/strong-baseline/synthetic-memory-cases-v1.sha256").read_text().split()[0]
    assert sha256(corpus) == expected

    resources = json.loads((ROOT / "results/strong-baseline/resource-accounting.json").read_text())
    assert resources["new_monetary_cost_usd"] == 0.0
    assert resources["paid_api_used"] is False
    assert resources["cloud_gpu_used"] is False

    verdict = json.loads((ROOT / "results/strong-baseline/reproduction-verdict.json").read_text())
    assert verdict["verdict"] in ALLOWED_VERDICTS
    if verdict["end_to_end_execution"] is not True:
        assert verdict["formal_answer_accuracy_permitted"] is False

    registry = json.loads((ROOT / "results/strong-baseline/artifact-registry.json").read_text())
    for artifact in registry["artifacts"]:
        path = ROOT / artifact["path"]
        assert path.is_file(), artifact["path"]
        assert path.stat().st_size == artifact["bytes"], artifact["path"]
        assert sha256(path) == artifact["sha256"], artifact["path"]

    forbidden = ("longmemeval-s-sealed_final", "sealed-final payload")
    for artifact in registry["artifacts"]:
        text = (ROOT / artifact["path"]).read_text(errors="ignore").lower()
        assert not any(marker in text for marker in forbidden), artifact["path"]

    print(f"strong-baseline verification PASS ({len(registry['artifacts'])} artifacts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
