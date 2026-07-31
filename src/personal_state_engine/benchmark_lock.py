from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


class BenchmarkIntegrityError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class BenchmarkLock:
    version: str
    files: dict[str, str]
    scenario_count: int
    split_counts: dict[str, int]


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_scenarios(path: str | Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        required = {"id", "category", "description", "expected", "split"}
        missing = required.difference(row)
        if missing:
            raise BenchmarkIntegrityError(f"line {line_number}: missing {sorted(missing)}")
        if row["id"] in seen:
            raise BenchmarkIntegrityError(f"line {line_number}: duplicate id {row['id']}")
        if row["split"] not in {"development", "validation", "pilot_test"}:
            raise BenchmarkIntegrityError(f"line {line_number}: invalid split {row['split']}")
        seen.add(str(row["id"]))
        rows.append(row)
    return rows


def create_lock(
    files: list[str | Path],
    *,
    scenarios_path: str | Path,
    version: str,
) -> BenchmarkLock:
    scenarios = load_scenarios(scenarios_path)
    split_counts: dict[str, int] = {}
    for row in scenarios:
        split = str(row["split"])
        split_counts[split] = split_counts.get(split, 0) + 1
    hashes = {Path(path).as_posix(): sha256_file(path) for path in files}
    return BenchmarkLock(version, hashes, len(scenarios), split_counts)


def write_lock(lock: BenchmarkLock, destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": lock.version,
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


def verify_lock(lock_path: str | Path, *, root: str | Path = ".") -> BenchmarkLock:
    data = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    lock = BenchmarkLock(
        version=data["version"],
        files=data["files"],
        scenario_count=data["scenario_count"],
        split_counts=data["split_counts"],
    )
    root = Path(root)
    mismatches: list[str] = []
    for relative, expected in lock.files.items():
        path = root / relative
        if not path.exists():
            mismatches.append(f"missing:{relative}")
        elif sha256_file(path) != expected:
            mismatches.append(f"hash:{relative}")
    if mismatches:
        raise BenchmarkIntegrityError(", ".join(mismatches))
    return lock
