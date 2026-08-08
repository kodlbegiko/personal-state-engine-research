#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/zero-cost-algorithm/artifact-registry.json"
GENERATED_AT = "2026-08-08T23:40:00Z"

ARTIFACT_PATHS = [
    "results/zero-cost-algorithm/baseline-results.json",
    "results/zero-cost-algorithm/ablation-results.json",
    "results/zero-cost-algorithm/statistical-analysis.json",
    "results/zero-cost-algorithm/failure-analysis.json",
    "results/zero-cost-algorithm/robustness-results.json",
    "results/zero-cost-algorithm/determinism-report.json",
    "results/zero-cost-algorithm/reproduction-status.json",
    "benchmarks/strong-baseline/synthetic-memory-cases-v1.json",
    "benchmarks/algorithm-development/specification-v2.json",
    "benchmarks/algorithm-development/withheld-extension-v2.json",
    "benchmarks/algorithm-development/freeze-manifest-v2.json",
    "results/current-environment-audit.json",
    "results/zero-cost-algorithm/resource-accounting.json",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    artifacts = []
    for relative in ARTIFACT_PATHS:
        if "sealed-final" in relative or "sealed_final" in relative:
            raise RuntimeError(f"sealed-final path forbidden in registry: {relative}")
        path = ROOT / relative
        if not path.is_file():
            raise RuntimeError(f"missing zero-cost artifact: {relative}")
        artifacts.append({
            "bytes": path.stat().st_size,
            "path": relative,
            "sha256": sha256_file(path),
        })
    payload = {
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "generated_at": GENERATED_AT,
        "generation_command": "python scripts/run_zero_cost_algorithm_research.py && python scripts/refresh_zero_cost_artifact_registry.py",
        "hash_algorithm": "sha256",
        "paid_api_cost_usd": 0.0,
        "schema_version": "zero-cost-algorithm-artifact-registry-v1",
        "sealed_final_accessed": False,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ZERO_COST_REGISTRY_REFRESHED", "artifact_count": len(artifacts)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
