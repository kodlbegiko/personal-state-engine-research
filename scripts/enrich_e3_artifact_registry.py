#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


class RegistryError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _artifact_ids(entries: list[dict[str, Any]], artifact_type: str) -> list[str]:
    return [
        str(entry["artifact_id"])
        for entry in entries
        if entry.get("artifact_type") == artifact_type
    ]


def enrich_registry(
    run_directory: Path,
    *,
    source_manifest_path: Path,
    model_manifest_path: Path,
    run_manifest_path: Path,
    source_head_sha: str,
    tested_commit_sha: str,
    workflow_run_id: str | None,
    workflow_run_attempt: str | None,
    github_artifact_id: str | None = None,
    github_artifact_digest: str | None = None,
) -> dict[str, Any]:
    registry_path = run_directory / "artifact-registry.json"
    if not registry_path.is_file():
        raise RegistryError(f"missing registry: {registry_path}")

    source_manifest = read_json(source_manifest_path)
    expected_dataset_hash = str(source_manifest["expected_sha256"])
    model_manifest_hash = sha256_file(model_manifest_path)
    run_manifest_hash = sha256_file(run_manifest_path)

    payload = read_json(registry_path)
    entries = payload.get("artifacts")
    if not isinstance(entries, list) or not entries:
        raise RegistryError("registry has no artifact entries")

    dataset_audit_ids = _artifact_ids(entries, "dataset-audit")
    smoke_ids = _artifact_ids(entries, "smoke-selection")
    cache_ids = _artifact_ids(entries, "model-cache-manifest")
    environment_ids = _artifact_ids(entries, "environment-manifest")
    raw_trial_ids = _artifact_ids(entries, "raw-trial")

    if not dataset_audit_ids or not smoke_ids or not environment_ids:
        raise RegistryError("registry is missing core provenance artifacts")

    for entry in entries:
        path = Path(str(entry["path"]))
        if not path.is_file():
            raise RegistryError(f"registry path does not exist: {path}")
        observed_sha = sha256_file(path)
        if entry.get("sha256") != observed_sha:
            raise RegistryError(f"registry SHA mismatch: {path}")

        artifact_type = str(entry.get("artifact_type"))
        entry["source_head_sha"] = source_head_sha
        entry["tested_commit_sha"] = tested_commit_sha
        entry["code_commit"] = tested_commit_sha
        entry["dataset_hash"] = expected_dataset_hash
        entry["model_manifest_hash"] = model_manifest_hash
        entry["config_hash"] = run_manifest_hash

        sources: list[str] = list(entry.get("source_artifacts") or [])
        if artifact_type == "split-manifest":
            sources.extend(dataset_audit_ids)
        elif artifact_type == "smoke-selection":
            sources.extend(dataset_audit_ids)
            sources.extend(_artifact_ids(entries, "split-manifest"))
        elif artifact_type == "model-cache-manifest":
            sources.extend([])
        elif artifact_type == "environment-manifest":
            sources.extend(cache_ids)
        elif artifact_type == "raw-trial":
            trial = read_json(path)
            trial_dataset = trial.get("dataset_sha256")
            trial_config = trial.get("configuration_sha256")
            if trial_dataset != expected_dataset_hash:
                raise RegistryError(f"raw trial dataset hash mismatch: {path}")
            if not isinstance(trial_config, str) or len(trial_config) != 64:
                raise RegistryError(f"raw trial missing configuration hash: {path}")
            entry["dataset_hash"] = trial_dataset
            entry["config_hash"] = trial_config
            sources.extend(dataset_audit_ids + smoke_ids + cache_ids + environment_ids)
        elif artifact_type == "processed-summary":
            sources.extend(raw_trial_ids + smoke_ids + environment_ids)

        entry["source_artifacts"] = sorted(set(sources))

    for entry in entries:
        if entry.get("artifact_type") in {"raw-trial", "processed-summary"}:
            for field in ("dataset_hash", "model_manifest_hash", "config_hash"):
                if not entry.get(field):
                    raise RegistryError(
                        f"{entry['artifact_id']} has null required provenance field {field}"
                    )
        if entry.get("artifact_type") == "raw-trial" and not entry.get("source_artifacts"):
            raise RegistryError(f"{entry['artifact_id']} has no source artifacts")

    enriched = {
        "schema_version": "artifact-registry-v2",
        "metadata": {
            "workflow_run_id": workflow_run_id,
            "workflow_run_attempt": workflow_run_attempt,
            "source_head_sha": source_head_sha,
            "tested_commit_sha": tested_commit_sha,
            "github_artifact_id": github_artifact_id,
            "github_artifact_digest": github_artifact_digest,
            "post_upload_metadata_status": (
                "COMPLETE"
                if github_artifact_id and github_artifact_digest
                else "PENDING_POST_UPLOAD"
            ),
            "post_upload_metadata_limitation": (
                None
                if github_artifact_id and github_artifact_digest
                else "GitHub artifact ID/digest do not exist until upload completes; populate from a post-upload archival step."
            ),
        },
        "artifacts": entries,
    }
    write_json(registry_path, enriched)
    return enriched


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich and validate E3 artifact provenance.")
    parser.add_argument("--output-root", type=Path, default=Path("results/e3-smoke"))
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--model-manifest", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--source-head-sha", required=True)
    parser.add_argument("--tested-commit-sha", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_directories = sorted(
        path for path in args.output_root.glob("e3-smoke-*") if path.is_dir()
    )
    if len(run_directories) != 1:
        raise RegistryError(
            f"expected exactly one E3 smoke run directory, found {len(run_directories)}"
        )
    payload = enrich_registry(
        run_directories[0],
        source_manifest_path=args.source_manifest,
        model_manifest_path=args.model_manifest,
        run_manifest_path=args.run_manifest,
        source_head_sha=args.source_head_sha,
        tested_commit_sha=args.tested_commit_sha,
        workflow_run_id=os.environ.get("GITHUB_RUN_ID"),
        workflow_run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
    )
    print(
        json.dumps(
            {
                "status": "E3_ARTIFACT_REGISTRY_PROVENANCE_PASS",
                "schema_version": payload["schema_version"],
                "artifact_count": len(payload["artifacts"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
