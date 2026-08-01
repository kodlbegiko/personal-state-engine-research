from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from personal_state_engine.longmemeval_faithful_port import (
    EXPECTED_CASE_ID_SHA256,
    OFFICIAL_LOCAL_MODEL,
    OFFICIAL_OPENAI_MODEL,
    OFFICIAL_SOURCE_BLOB_SHA,
    OFFICIAL_SOURCE_COMMIT,
    OFFICIAL_SOURCE_PATH,
    OFFICIAL_SOURCE_SHA256,
    canonical_json,
    sha256_file,
    verify_blinded_records,
)
from prepare_longmemeval_faithful_port import OUTPUT_DIRECTORY, prepare

EXPECTED_FILES = {
    "README.md",
    "raw-evidence-integrity.json",
    "immutable-answer-manifest.json",
    "official-source-manifest.json",
    "official-source-snapshot.sha256",
    "official-prompt-bundle.json",
    "official-prompt-bundle.sha256",
    "faithful-port-deviations.json",
    "evaluator-manifest.json",
    "parser-manifest.json",
    "blinding-manifest.json",
    "unit-test-corpus-manifest.json",
    "environment-capability.json",
    "blinded-inputs.jsonl",
    "unblinding-key.json",
    "artifact-registry.json",
    "preparation-verdict.json",
}
FORBIDDEN_OUTPUT_NAMES = {"formal-summary.json", "formal-rescoring.jsonl", "paired-analysis.json"}
FORBIDDEN_PAYLOAD_SUFFIXES = {".bin", ".gguf", ".onnx", ".safetensors", ".pt", ".pth"}
SECRET_MARKERS = ("sk-proj-", "sk-live-", "OPENAI_API_KEY=")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {path}:{index}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"JSONL row is not an object at {path}:{index}")
        rows.append(row)
    return rows


def _verify_registry(output_root: Path) -> None:
    registry = _load_json(output_root / "artifact-registry.json")
    entries = registry.get("artifacts", [])
    if registry.get("artifact_count") != len(entries):
        raise ValueError("artifact registry count mismatch")
    registered = set()
    for item in entries:
        relative = item["path"]
        path = output_root / relative
        registered.add(relative)
        if not path.is_file():
            raise ValueError(f"registered artifact missing: {relative}")
        if path.stat().st_size != item["size_bytes"]:
            raise ValueError(f"registered size mismatch: {relative}")
        if sha256_file(path) != item["sha256"]:
            raise ValueError(f"registered hash mismatch: {relative}")
    actual = {
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*")
        if path.is_file() and path.name != "artifact-registry.json"
    }
    if registered != actual:
        raise ValueError(f"artifact registry coverage mismatch: missing={sorted(actual-registered)}, extra={sorted(registered-actual)}")


def _verify_regeneration(repo_root: Path, output_root: Path) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        regenerated = Path(temporary) / "generated"
        prepare(repo_root, regenerated)
        original_files = {
            path.relative_to(output_root).as_posix(): path.read_bytes()
            for path in output_root.rglob("*")
            if path.is_file()
        }
        regenerated_files = {
            path.relative_to(regenerated).as_posix(): path.read_bytes()
            for path in regenerated.rglob("*")
            if path.is_file()
        }
        if original_files != regenerated_files:
            differing = sorted(set(original_files) ^ set(regenerated_files))
            for path in sorted(set(original_files) & set(regenerated_files)):
                if original_files[path] != regenerated_files[path]:
                    differing.append(path)
            raise ValueError("clean regeneration mismatch: " + ", ".join(differing))


def verify(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_root = repo_root / OUTPUT_DIRECTORY
    if not output_root.is_dir():
        raise ValueError(f"missing preparation directory: {OUTPUT_DIRECTORY}")
    actual_names = {path.name for path in output_root.iterdir() if path.is_file()}
    if actual_names != EXPECTED_FILES:
        raise ValueError(f"unexpected preparation file set: {sorted(actual_names ^ EXPECTED_FILES)}")
    if FORBIDDEN_OUTPUT_NAMES.intersection(actual_names):
        raise ValueError("formal v3 result files are prohibited in preparation output")

    integrity = _load_json(output_root / "raw-evidence-integrity.json")
    if integrity["integrity_verdict"] != "PASS" or integrity["observed_raw_trials"] != 40:
        raise ValueError("raw evidence integrity is not PASS for 40 trials")
    if integrity["case_id_sha256"] != EXPECTED_CASE_ID_SHA256:
        raise ValueError("case-ID hash mismatch")
    if integrity["sealed_final_accessed"] is not False or integrity["answer_model_rerun"] is not False:
        raise ValueError("sealed-final or answer-model execution boundary violated")

    source = _load_json(output_root / "official-source-manifest.json")
    expected_source = {
        "official_commit_sha": OFFICIAL_SOURCE_COMMIT,
        "official_file_path": OFFICIAL_SOURCE_PATH,
        "official_file_blob_sha": OFFICIAL_SOURCE_BLOB_SHA,
        "official_file_sha256": OFFICIAL_SOURCE_SHA256,
    }
    for key, value in expected_source.items():
        if source.get(key) != value:
            raise ValueError(f"official source pin mismatch: {key}")

    snapshot_hash = (output_root / "official-source-snapshot.sha256").read_text(encoding="utf-8").strip()
    if snapshot_hash != OFFICIAL_SOURCE_SHA256:
        raise ValueError("official source snapshot hash mismatch")

    evaluator = _load_json(output_root / "evaluator-manifest.json")
    if evaluator.get("source_type") != "faithful-port":
        raise ValueError("evaluator source_type must be faithful-port")
    if evaluator.get("model_id") != OFFICIAL_OPENAI_MODEL:
        raise ValueError("primary official model is not exact-pinned")
    if evaluator.get("allowed_alternate_official_model") != OFFICIAL_LOCAL_MODEL:
        raise ValueError("official local alternate is not exact-pinned")
    serialized_evaluator = canonical_json(evaluator).lower()
    for forbidden in ("llama-3.2-3b", "qwen", "fallback_model"):
        if forbidden in serialized_evaluator:
            raise ValueError(f"prohibited smaller judge path present: {forbidden}")

    parser_manifest = _load_json(output_root / "parser-manifest.json")
    if parser_manifest.get("results") != ["CORRECT", "INCORRECT", "INVALID"]:
        raise ValueError("parser result enum mismatch")
    if parser_manifest.get("invalid_default") is not None or parser_manifest.get("fuzzy_matching") is not False:
        raise ValueError("invalid outputs must not be coerced or fuzzy-matched")

    blinded = _load_jsonl(output_root / "blinded-inputs.jsonl")
    key_document = _load_json(output_root / "unblinding-key.json")
    leakage = _load_json(output_root / "blinding-manifest.json").get("answer_originated_identity_leakage", [])
    verify_blinded_records(blinded, key_document["rows"], allowed_answer_originated_leakage=leakage)

    unit_manifest = _load_json(output_root / "unit-test-corpus-manifest.json")
    if unit_manifest.get("case_count", 0) < 24 or unit_manifest.get("formal_output_copying") is not False:
        raise ValueError("unit corpus is too small or not independent")

    verdict = _load_json(output_root / "preparation-verdict.json")
    if verdict.get("preparation_verdict") not in {"READY FOR FRESH BLINDED CALIBRATION", "BLOCKED BY ENVIRONMENT"}:
        raise ValueError("invalid preparation verdict")
    if verdict.get("evaluator_calibration") != "NOT YET ESTABLISHED":
        raise ValueError("v3 calibration must remain not established")
    if verdict.get("formal_correctness_use_for_v3") != "PROHIBITED":
        raise ValueError("formal v3 correctness use must remain prohibited")

    for path in output_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in FORBIDDEN_PAYLOAD_SUFFIXES:
            raise ValueError(f"model/dataset payload prohibited: {path.name}")
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(marker in text for marker in SECRET_MARKERS):
            raise ValueError(f"secret marker detected: {path.name}")

    _verify_registry(output_root)
    _verify_regeneration(repo_root, output_root)
    return {
        "schema_version": "longmemeval-faithful-port-preparation-verification-v3",
        "verdict": "PASS",
        "raw_trial_count": integrity["observed_raw_trials"],
        "unit_case_count": unit_manifest["case_count"],
        "preparation_verdict": verdict["preparation_verdict"],
        "clean_regeneration": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = verify(args.repo_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
