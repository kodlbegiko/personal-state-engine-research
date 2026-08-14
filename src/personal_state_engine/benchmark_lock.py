from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class BenchmarkIntegrityError(ValueError):
    pass


_SUPPORTED_HASH_ALGORITHMS = {"sha256", "git_blob_sha1"}


@dataclass(frozen=True, slots=True)
class BenchmarkLock:
    version: str
    files: dict[str, str]
    scenario_count: int
    split_counts: dict[str, int]
    hash_algorithm: str = "sha256"


def _file_bytes(path: str | Path) -> bytes:
    return Path(path).read_bytes()


def hash_file(path: str | Path, algorithm: str = "sha256") -> str:
    if algorithm == "sha256":
        return hashlib.sha256(_file_bytes(path)).hexdigest()
    if algorithm == "git_blob_sha1":
        content = _file_bytes(path)
        header = f"blob {len(content)}\0".encode("ascii")
        return hashlib.sha1(header + content, usedforsecurity=False).hexdigest()
    raise BenchmarkIntegrityError(f"unsupported hash algorithm: {algorithm}")


def sha256_file(path: str | Path) -> str:
    """Backward-compatible SHA-256 helper used by existing callers."""
    return hash_file(path, "sha256")


def _normalise_relative_path(path: str | Path, *, root: Path) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            candidate = candidate.relative_to(root.resolve())
        except ValueError as exc:
            raise BenchmarkIntegrityError(f"path is outside root: {path}") from exc
    if not candidate.parts or ".." in candidate.parts:
        raise BenchmarkIntegrityError(f"unsafe lock path: {path}")
    return candidate.as_posix()


def pilot_lock_paths(root: str | Path = ".") -> tuple[str, ...]:
    """Return the complete current deterministic-pilot integrity boundary.

    The boundary intentionally includes every package module and every Python
    runner, rather than relying on an incomplete hand-maintained transitive list.
    """
    root_path = Path(root)
    paths = {
        path.relative_to(root_path).as_posix()
        for pattern in ("src/personal_state_engine/*.py", "scripts/*.py")
        for path in root_path.glob(pattern)
        if path.is_file()
    }
    paths.update(
        {
            "benchmarks/synthetic/scenarios.jsonl",
            "benchmarks/redteam/memory-write-policy.jsonl",
        }
    )
    return tuple(sorted(paths))


def load_scenarios(path: str | Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BenchmarkIntegrityError(
                f"line {line_number}: invalid scenario JSON"
            ) from exc
        if not isinstance(row, dict):
            raise BenchmarkIntegrityError(f"line {line_number}: scenario must be an object")
        required = {"id", "category", "description", "expected", "split"}
        missing = required.difference(row)
        if missing:
            raise BenchmarkIntegrityError(f"line {line_number}: missing {sorted(missing)}")
        scenario_id = str(row["id"])
        if scenario_id in seen:
            raise BenchmarkIntegrityError(f"line {line_number}: duplicate id {scenario_id}")
        if row["split"] not in {"development", "validation", "pilot_test"}:
            raise BenchmarkIntegrityError(
                f"line {line_number}: invalid split {row['split']}"
            )
        seen.add(scenario_id)
        rows.append(row)
    return rows


def create_lock(
    files: Iterable[str | Path],
    *,
    scenarios_path: str | Path,
    version: str,
    root: str | Path = ".",
    hash_algorithm: str = "sha256",
) -> BenchmarkLock:
    if hash_algorithm not in _SUPPORTED_HASH_ALGORITHMS:
        raise BenchmarkIntegrityError(f"unsupported hash algorithm: {hash_algorithm}")
    if not isinstance(version, str) or not version.strip():
        raise BenchmarkIntegrityError("benchmark version is required")
    root_path = Path(root)
    scenarios = load_scenarios(root_path / scenarios_path)
    split_counts: dict[str, int] = {}
    for row in scenarios:
        split = str(row["split"])
        split_counts[split] = split_counts.get(split, 0) + 1
    hashes: dict[str, str] = {}
    for path in files:
        relative = _normalise_relative_path(path, root=root_path)
        if relative in hashes:
            raise BenchmarkIntegrityError(f"duplicate lock path: {relative}")
        target = root_path / relative
        if not target.is_file():
            raise BenchmarkIntegrityError(f"missing lock input: {relative}")
        hashes[relative] = hash_file(target, hash_algorithm)
    return BenchmarkLock(
        version.strip(), hashes, len(scenarios), split_counts, hash_algorithm
    )


def write_lock(lock: BenchmarkLock, destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": lock.version,
                "hash_algorithm": lock.hash_algorithm,
                "files": lock.files,
                "scenario_count": lock.scenario_count,
                "split_counts": lock.split_counts,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def write_lock_anchor(lock_path: str | Path, destination: str | Path) -> Path:
    lock_path = Path(lock_path)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        f"{sha256_file(lock_path)}  {lock_path.as_posix()}\n", encoding="utf-8"
    )
    return destination


def verify_lock_anchor(anchor_path: str | Path, lock_path: str | Path) -> str:
    try:
        line = Path(anchor_path).read_text(encoding="utf-8").strip()
        expected, recorded_path = line.split(maxsplit=1)
    except (OSError, ValueError) as exc:
        raise BenchmarkIntegrityError("invalid benchmark lock anchor") from exc
    expected = expected.strip().lower()
    recorded_path = recorded_path.strip()
    if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
        raise BenchmarkIntegrityError("invalid benchmark lock anchor digest")
    if recorded_path != Path(lock_path).as_posix():
        raise BenchmarkIntegrityError("benchmark lock anchor path mismatch")
    actual = sha256_file(lock_path)
    if actual != expected:
        raise BenchmarkIntegrityError("benchmark lock anchor hash mismatch")
    return actual


def load_lock(lock_path: str | Path) -> BenchmarkLock:
    try:
        data = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError("benchmark lock is not readable valid JSON") from exc
    if not isinstance(data, dict):
        raise BenchmarkIntegrityError("benchmark lock root must be an object")
    try:
        algorithm = data.get("hash_algorithm", "sha256")
        lock = BenchmarkLock(
            version=data["version"],
            files=data["files"],
            scenario_count=data["scenario_count"],
            split_counts=data["split_counts"],
            hash_algorithm=algorithm,
        )
    except (KeyError, TypeError) as exc:
        raise BenchmarkIntegrityError("benchmark lock schema is invalid") from exc
    if lock.hash_algorithm not in _SUPPORTED_HASH_ALGORITHMS:
        raise BenchmarkIntegrityError(
            f"unsupported hash algorithm: {lock.hash_algorithm}"
        )
    if not isinstance(lock.files, dict) or not lock.files:
        raise BenchmarkIntegrityError("benchmark lock files must be a non-empty object")
    digest_length = 64 if lock.hash_algorithm == "sha256" else 40
    for relative, digest in lock.files.items():
        _normalise_relative_path(relative, root=Path("."))
        if (
            not isinstance(digest, str)
            or len(digest) != digest_length
            or any(char not in "0123456789abcdef" for char in digest.lower())
        ):
            raise BenchmarkIntegrityError(f"invalid digest for {relative}")
    return lock


def verify_lock(
    lock_path: str | Path,
    *,
    root: str | Path = ".",
    expected_paths: Iterable[str] | None = None,
) -> BenchmarkLock:
    lock = load_lock(lock_path)
    root_path = Path(root)
    mismatches: list[str] = []
    if expected_paths is not None:
        expected_set = {Path(path).as_posix() for path in expected_paths}
        locked_set = set(lock.files)
        for relative in sorted(expected_set - locked_set):
            mismatches.append(f"unlocked:{relative}")
        for relative in sorted(locked_set - expected_set):
            mismatches.append(f"unexpected:{relative}")
    for relative, expected in lock.files.items():
        path = root_path / relative
        if not path.is_file():
            mismatches.append(f"missing:{relative}")
        elif hash_file(path, lock.hash_algorithm) != expected:
            mismatches.append(f"hash:{relative}")
    scenarios_relative = "benchmarks/synthetic/scenarios.jsonl"
    if scenarios_relative in lock.files and (root_path / scenarios_relative).is_file():
        scenarios = load_scenarios(root_path / scenarios_relative)
        split_counts: dict[str, int] = {}
        for row in scenarios:
            split = str(row["split"])
            split_counts[split] = split_counts.get(split, 0) + 1
        if len(scenarios) != lock.scenario_count:
            mismatches.append("scenario_count")
        if split_counts != lock.split_counts:
            mismatches.append("split_counts")
    if mismatches:
        raise BenchmarkIntegrityError(", ".join(mismatches))
    return lock
