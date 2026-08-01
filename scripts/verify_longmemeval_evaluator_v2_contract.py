#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()

    root = args.output_root
    required = [
        "README.md",
        "evaluator-manifest.json",
        "official-source-audit.json",
        "provider-selection.json",
        "prompt-templates.json",
        "parser-version.json",
        "human-audit-completed-blinded.json",
        "human-audit-key.json",
        "blinded-inputs.jsonl",
        "blinding-key.json",
        "research-verdict.json",
        "artifact-registry.json",
    ]
    for relative in required:
        path = root / relative
        if not path.is_file():
            raise SystemExit(f"missing required evaluator artifact: {relative}")

    registry = load_json(root / "artifact-registry.json")
    if registry["artifact_count"] != len(registry["artifacts"]):
        raise SystemExit("artifact registry count mismatch")
    for item in registry["artifacts"]:
        path = root / item["path"]
        if not path.is_file():
            raise SystemExit(f"registered file missing: {item['path']}")
        if path.stat().st_size != item["size_bytes"]:
            raise SystemExit(f"registered size mismatch: {item['path']}")
        if sha256(path) != item["sha256"]:
            raise SystemExit(f"registered hash mismatch: {item['path']}")

    verdict = load_json(root / "research-verdict.json")
    if verdict["answer_model_rerun"] is not False:
        raise SystemExit("answer model rerun flag must remain false")
    if verdict["case_ids_changed"] is not False:
        raise SystemExit("case IDs changed flag must remain false")
    if verdict["sealed_final_accessed"] is not False:
        raise SystemExit("sealed-final access must remain false")
    if verdict["old_failed_evaluator_preserved"] is not True:
        raise SystemExit("old failed evaluator evidence must remain preserved")

    old_required = [
        "evaluator-calibration.json",
        "research-verdict.json",
        "human-audit-completed-blinded.json",
        "human-audit-key.json",
    ]
    for relative in old_required:
        if not (args.evidence_root / relative).is_file():
            raise SystemExit(f"old evidence missing: {relative}")

    blinded_lines = [json.loads(line) for line in (root / "blinded-inputs.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(blinded_lines) != 40:
        raise SystemExit(f"expected 40 blinded inputs, found {len(blinded_lines)}")
    forbidden = ("EXT-B0", "EXT-B5", "no-memory", "retrieval", "baseline", "control", "treatment")
    for row in blinded_lines:
        serialized = json.dumps(row, ensure_ascii=False).lower()
        for term in forbidden:
            if term.lower() in serialized:
                raise SystemExit(f"baseline identity leakage in blinded input {row['blinded_response_id']}: {term}")

    verdict_name = verdict["research_verdict"]
    if verdict_name == "BLOCKED BY ENVIRONMENT":
        if not (root / "environment-blocker.json").is_file():
            raise SystemExit("environment blocker verdict lacks environment-blocker.json")
        result = {
            "status": "PASS",
            "research_verdict": verdict_name,
            "formal_correctness_use": "PROHIBITED",
            "artifact_count": registry["artifact_count"],
            "blinded_inputs": 40,
        }
        print(json.dumps(result, sort_keys=True))
        return 0

    calibration_path = root / "evaluator-calibration.json"
    if not calibration_path.is_file():
        raise SystemExit("executed evaluator lacks calibration report")
    calibration = load_json(calibration_path)
    parsed_formal = root / "parsed-judgments/formal.jsonl"
    if not parsed_formal.is_file():
        raise SystemExit("formal parsed judgments missing")
    parsed_rows = [json.loads(line) for line in parsed_formal.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(parsed_rows) != 40:
        raise SystemExit(f"expected 40 formal parsed judgments, found {len(parsed_rows)}")
    if len({row["blinded_response_id"] for row in parsed_rows}) != 40:
        raise SystemExit("formal parsed judgment IDs are not unique")
    raw_formal = list((root / "raw-judge-outputs/formal").glob("*.json"))
    if len(raw_formal) != 40:
        raise SystemExit(f"expected 40 preserved raw formal judge outputs, found {len(raw_formal)}")

    calibration_pass = calibration["calibration_verdict"] == "PASS"
    if calibration_pass:
        for relative in ("formal-rescoring.jsonl", "formal-summary.json", "paired-analysis.json"):
            if not (root / relative).is_file():
                raise SystemExit(f"calibration passed but {relative} is missing")
        if verdict["formal_correctness_use"] != "PERMITTED":
            raise SystemExit("calibration passed but formal correctness is not permitted")
    else:
        if not (root / "formal-rescoring-prohibited.json").is_file():
            raise SystemExit("calibration failed but prohibition artifact is missing")
        if verdict["formal_correctness_use"] != "PROHIBITED":
            raise SystemExit("calibration failed but formal correctness was not prohibited")
        if (root / "formal-summary.json").exists() or (root / "paired-analysis.json").exists():
            raise SystemExit("formal aggregate results exist despite failed calibration")

    if list(root.rglob("*.onnx")) or list(root.rglob("*.safetensors")) or list(root.rglob("*.bin")):
        raise SystemExit("model payload entered evaluator evidence directory")

    result = {
        "status": "PASS",
        "research_verdict": verdict_name,
        "calibration_verdict": calibration["calibration_verdict"],
        "formal_correctness_use": verdict["formal_correctness_use"],
        "artifact_count": registry["artifact_count"],
        "raw_formal_outputs": len(raw_formal),
        "parsed_formal_outputs": len(parsed_rows),
        "blinded_inputs": len(blinded_lines),
        "sealed_final_accessed": False,
        "answer_model_rerun": False,
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
