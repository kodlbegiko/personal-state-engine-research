from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from .models import MemoryKind, MemoryRecord, MemoryStatus, Provenance, SourceType

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_metadata (
    schema_version INTEGER NOT NULL
);
INSERT INTO schema_metadata(schema_version)
    SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM schema_metadata);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    memory_key TEXT NOT NULL,
    content TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_location TEXT,
    user_confirmed INTEGER NOT NULL,
    externally_verified INTEGER NOT NULL,
    conflict INTEGER NOT NULL,
    sensitive INTEGER NOT NULL,
    allow_long_term INTEGER NOT NULL,
    provenance_metadata TEXT NOT NULL,
    created_at TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    valid_from TEXT,
    valid_until TEXT,
    last_confirmed_at TEXT,
    supersedes TEXT,
    superseded_by TEXT,
    version INTEGER NOT NULL,
    status TEXT NOT NULL,
    confidence REAL NOT NULL,
    tags TEXT NOT NULL,
    project TEXT
);
CREATE INDEX IF NOT EXISTS memories_user_status
    ON memories(user_id, status);
CREATE INDEX IF NOT EXISTS memories_user_key
    ON memories(user_id, memory_key);

CREATE TABLE IF NOT EXISTS search_index (
    memory_id TEXT PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    search_text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS search_user
    ON search_index(user_id);

CREATE TABLE IF NOT EXISTS audit_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    memory_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def normalise(value: str) -> str:
    return " ".join(value.casefold().split())


def to_values(record: MemoryRecord) -> tuple[object, ...]:
    p = record.provenance
    return (
        record.id, record.user_id, record.kind.value, record.key, record.content,
        p.source_type.value, p.source_id, p.source_location,
        int(p.user_confirmed), int(p.externally_verified), int(p.conflict),
        int(p.sensitive), int(p.allow_long_term), json.dumps(p.metadata, sort_keys=True),
        iso(record.created_at), iso(record.observed_at), iso(record.valid_from),
        iso(record.valid_until), iso(record.last_confirmed_at), record.supersedes,
        record.superseded_by, record.version, record.status.value, record.confidence,
        json.dumps(record.tags), record.project,
    )


def from_row(row: sqlite3.Row) -> MemoryRecord:
    provenance = Provenance(
        source_type=SourceType(row["source_type"]),
        source_id=row["source_id"],
        source_location=row["source_location"],
        user_confirmed=bool(row["user_confirmed"]),
        externally_verified=bool(row["externally_verified"]),
        conflict=bool(row["conflict"]),
        sensitive=bool(row["sensitive"]),
        allow_long_term=bool(row["allow_long_term"]),
        metadata=json.loads(row["provenance_metadata"]),
    )
    return MemoryRecord(
        id=row["id"], user_id=row["user_id"], kind=MemoryKind(row["kind"]),
        key=row["memory_key"], content=row["content"], provenance=provenance,
        created_at=parse(row["created_at"]), observed_at=parse(row["observed_at"]),
        valid_from=parse(row["valid_from"]), valid_until=parse(row["valid_until"]),
        last_confirmed_at=parse(row["last_confirmed_at"]), supersedes=row["supersedes"],
        superseded_by=row["superseded_by"], version=row["version"],
        status=MemoryStatus(row["status"]), confidence=row["confidence"],
        tags=tuple(json.loads(row["tags"])), project=row["project"],
    )
