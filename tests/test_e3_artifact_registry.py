from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "enrich_e3_artifact_registry.py"
SPEC = importlib.util.spec_from_file_location("e3_registry", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


class E3ArtifactRegistryTests(unittest.TestCase):
    def test_enrichment_populates_required_provenance_and_validates_raw_trial(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "results" / "e3-smoke" / "e3-smoke-123-attempt-1"
            run_dir.mkdir(parents=True)

            source_manifest = root / "source.json"
            model_manifest = root / "model.json"
            run_manifest = root / "run.json"
            dataset_hash = "a" * 64
            write_json(source_manifest, {"expected_sha256": dataset_hash})
            write_json(model_manifest, {"model_id": "m", "model_revision": "b" * 40})
            write_json(run_manifest, {"run": "config"})

            dataset_audit = run_dir / "dataset-audit.json"
            smoke = run_dir / "splits" / "longmemeval-s-smoke.json"
            cache = run_dir / "model-cache-manifest.json"
            environment = run_dir / "environment-manifest.json"
            raw = run_dir / "raw-trials" / "trial.json"
            summary = run_dir / "processed-summary.json"

            write_json(dataset_audit, {"dataset": dataset_hash})
            write_json(smoke, {"case_ids": ["q1"]})
            write_json(cache, {"files": []})
            write_json(environment, {"github_sha": "c" * 40})
            write_json(
                raw,
                {
                    "dataset_sha256": dataset_hash,
                    "configuration_sha256": "d" * 64,
                },
            )
            write_json(summary, {"case_count": 1})

            def entry(path: Path, artifact_type: str) -> dict[str, object]:
                return {
                    "artifact_id": f"{artifact_type}:{path.as_posix()}",
                    "artifact_type": artifact_type,
                    "path": path.as_posix(),
                    "sha256": MODULE.sha256_file(path),
                    "source_artifacts": [],
                    "dataset_hash": None,
                    "model_manifest_hash": None,
                    "config_hash": None,
                }

            registry = {
                "schema_version": "artifact-registry-v1",
                "artifacts": [
                    entry(dataset_audit, "dataset-audit"),
                    entry(smoke, "smoke-selection"),
                    entry(cache, "model-cache-manifest"),
                    entry(environment, "environment-manifest"),
                    entry(raw, "raw-trial"),
                    entry(summary, "processed-summary"),
                ],
            }
            write_json(run_dir / "artifact-registry.json", registry)

            enriched = MODULE.enrich_registry(
                run_dir,
                source_manifest_path=source_manifest,
                model_manifest_path=model_manifest,
                run_manifest_path=run_manifest,
                source_head_sha="e" * 40,
                tested_commit_sha="f" * 40,
                workflow_run_id="123",
                workflow_run_attempt="1",
            )

            self.assertEqual(enriched["schema_version"], "artifact-registry-v2")
            self.assertEqual(
                enriched["metadata"]["post_upload_metadata_status"],
                "PENDING_POST_UPLOAD",
            )
            raw_entry = next(
                item for item in enriched["artifacts"] if item["artifact_type"] == "raw-trial"
            )
            self.assertEqual(raw_entry["dataset_hash"], dataset_hash)
            self.assertEqual(raw_entry["config_hash"], "d" * 64)
            self.assertTrue(raw_entry["model_manifest_hash"])
            self.assertTrue(raw_entry["source_artifacts"])
            self.assertEqual(raw_entry["source_head_sha"], "e" * 40)
            self.assertEqual(raw_entry["tested_commit_sha"], "f" * 40)

    def test_rejects_raw_trial_dataset_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            run_dir.mkdir()
            source_manifest = root / "source.json"
            model_manifest = root / "model.json"
            run_manifest = root / "run.json"
            write_json(source_manifest, {"expected_sha256": "a" * 64})
            write_json(model_manifest, {"m": 1})
            write_json(run_manifest, {"r": 1})

            files = {}
            for name, artifact_type in [
                ("dataset-audit.json", "dataset-audit"),
                ("smoke.json", "smoke-selection"),
                ("environment.json", "environment-manifest"),
                ("raw.json", "raw-trial"),
            ]:
                path = run_dir / name
                payload = (
                    {"dataset_sha256": "b" * 64, "configuration_sha256": "c" * 64}
                    if artifact_type == "raw-trial"
                    else {"ok": True}
                )
                write_json(path, payload)
                files[artifact_type] = path

            registry = {
                "schema_version": "artifact-registry-v1",
                "artifacts": [
                    {
                        "artifact_id": f"{kind}:{path}",
                        "artifact_type": kind,
                        "path": path.as_posix(),
                        "sha256": MODULE.sha256_file(path),
                        "source_artifacts": [],
                    }
                    for kind, path in files.items()
                ],
            }
            write_json(run_dir / "artifact-registry.json", registry)

            with self.assertRaises(MODULE.RegistryError):
                MODULE.enrich_registry(
                    run_dir,
                    source_manifest_path=source_manifest,
                    model_manifest_path=model_manifest,
                    run_manifest_path=run_manifest,
                    source_head_sha="e" * 40,
                    tested_commit_sha="f" * 40,
                    workflow_run_id="1",
                    workflow_run_attempt="1",
                )


if __name__ == "__main__":
    unittest.main()
