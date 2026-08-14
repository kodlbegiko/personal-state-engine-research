#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import BinaryIO, Callable


class DatasetFetchError(RuntimeError):
    pass


def load_source_manifest(path: str | Path) -> dict[str, object]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DatasetFetchError("dataset source manifest is not readable valid JSON") from exc
    if not isinstance(data, dict):
        raise DatasetFetchError("dataset source manifest must be an object")
    required = {
        "schema_version",
        "dataset_name",
        "source_repository",
        "source_revision",
        "source_file",
        "download_url",
        "license",
        "license_status",
        "expected_sha256",
        "expected_size_bytes",
        "local_filename",
    }
    missing = required.difference(data)
    if missing:
        raise DatasetFetchError(f"dataset source manifest missing fields: {sorted(missing)}")
    for field in required - {"expected_size_bytes"}:
        value = data[field]
        if not isinstance(value, str) or not value.strip():
            raise DatasetFetchError(f"{field} must be a non-blank string")
    digest = str(data["expected_sha256"]).lower()
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise DatasetFetchError("expected_sha256 must be a lowercase SHA-256 digest")
    size = data["expected_size_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise DatasetFetchError("expected_size_bytes must be a positive integer")
    url = str(data["download_url"])
    revision = str(data["source_revision"])
    if not url.startswith("https://") or revision not in url:
        raise DatasetFetchError("download_url must use HTTPS and contain source_revision")
    filename = Path(str(data["local_filename"]))
    if filename.is_absolute() or len(filename.parts) != 1 or ".." in filename.parts:
        raise DatasetFetchError("local_filename must be one safe relative filename")
    return data


def _default_open(url: str) -> BinaryIO:
    return urllib.request.urlopen(url, timeout=60)  # nosec: pinned HTTPS URL + hash check


def fetch_dataset(
    manifest_path: str | Path,
    output_directory: str | Path,
    *,
    opener: Callable[[str], BinaryIO] = _default_open,
    chunk_size: int = 1024 * 1024,
) -> Path:
    manifest = load_source_manifest(manifest_path)
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size <= 0:
        raise DatasetFetchError("chunk_size must be a positive integer")
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    destination = output_directory / str(manifest["local_filename"])
    if destination.exists():
        raise DatasetFetchError(f"refusing to overwrite existing dataset: {destination}")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".partial", dir=output_directory
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    digest = hashlib.sha256()
    size = 0
    try:
        with opener(str(manifest["download_url"])) as response, temporary_path.open("wb") as output:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                if not isinstance(chunk, bytes):
                    raise DatasetFetchError("download stream returned non-byte content")
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)
            output.flush()
            os.fsync(output.fileno())
    except (OSError, urllib.error.URLError) as exc:
        raise DatasetFetchError(f"dataset download failed: {exc}") from exc
    finally:
        if size != manifest["expected_size_bytes"] or digest.hexdigest() != manifest["expected_sha256"]:
            temporary_path.unlink(missing_ok=True)

    if size != manifest["expected_size_bytes"]:
        raise DatasetFetchError(
            f"dataset size mismatch: expected {manifest['expected_size_bytes']}, received {size}"
        )
    if digest.hexdigest() != manifest["expected_sha256"]:
        raise DatasetFetchError(
            f"dataset SHA-256 mismatch: expected {manifest['expected_sha256']}, received {digest.hexdigest()}"
        )
    temporary_path.replace(destination)
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch a pinned LongMemEval dataset and verify size and SHA-256."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("experiments/datasets/longmemeval-s-cleaned.json"),
    )
    parser.add_argument("--output-directory", type=Path, default=Path("data"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        output = fetch_dataset(args.manifest, args.output_directory)
    except DatasetFetchError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"status": "downloaded_and_verified", "path": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
