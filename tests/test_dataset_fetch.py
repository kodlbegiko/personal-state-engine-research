from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "fetch_longmemeval", Path("scripts/fetch_longmemeval.py")
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()


class DatasetFetchTests(unittest.TestCase):
    def write_manifest(self, directory: str, payload: bytes, **overrides) -> Path:
        revision = "a" * 40
        data = {
            "schema_version": "dataset-source-v1",
            "dataset_name": "test",
            "source_repository": "owner/dataset",
            "source_revision": revision,
            "source_file": "dataset.json",
            "download_url": f"https://example.invalid/{revision}/dataset.json",
            "license": "MIT",
            "license_status": "CAN_COMMIT_DERIVED_RESULTS",
            "expected_sha256": hashlib.sha256(payload).hexdigest(),
            "expected_size_bytes": len(payload),
            "local_filename": "dataset.json",
        }
        data.update(overrides)
        path = Path(directory) / "manifest.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_official_manifest_is_pinned_and_valid(self):
        manifest = MODULE.load_source_manifest(
            "experiments/datasets/longmemeval-s-cleaned.json"
        )
        self.assertEqual(
            manifest["source_revision"],
            "98d7416c24c778c2fee6e6f3006e7a073259d48f",
        )
        self.assertEqual(
            manifest["expected_sha256"],
            "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442",
        )
        self.assertEqual(manifest["expected_size_bytes"], 277383467)

    def test_fetch_writes_only_after_size_and_hash_match(self):
        payload = b'[{"question_id":"q1"}]'
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.write_manifest(directory, payload)
            output = MODULE.fetch_dataset(
                manifest,
                Path(directory) / "data",
                opener=lambda url: Response(payload),
                chunk_size=4,
            )
            self.assertEqual(output.read_bytes(), payload)

    def test_fetch_rejects_hash_mismatch_and_removes_partial(self):
        payload = b"expected"
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.write_manifest(
                directory,
                payload,
                expected_sha256=hashlib.sha256(b"different").hexdigest(),
            )
            output_directory = Path(directory) / "data"
            with self.assertRaisesRegex(MODULE.DatasetFetchError, "SHA-256 mismatch"):
                MODULE.fetch_dataset(
                    manifest,
                    output_directory,
                    opener=lambda url: Response(payload),
                )
            self.assertEqual(list(output_directory.iterdir()), [])

    def test_manifest_rejects_floating_url(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.write_manifest(
                directory,
                b"data",
                download_url="https://example.invalid/main/dataset.json",
            )
            with self.assertRaisesRegex(MODULE.DatasetFetchError, "source_revision"):
                MODULE.load_source_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
