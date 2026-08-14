from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from ._persistence_support import (
    SCHEMA_SQL,
    SCHEMA_VERSION,
    from_row,
    normalise,
    to_values,
)
from .models import MemoryRecord, MemoryStatus
from .policy import MemoryWritePolicy, PolicyDecision


class SQLiteMemoryStore:
    """Persistent, user-scoped memory store with deletion-aware derived indexes.

    SQLite uses ``secure_delete=ON`` and a non-WAL journal so completed
    deletions can be compacted without retaining plaintext in a WAL file.
    Audit events store content digests rather than original content.
    """

    def __init__(
        self,
        path: str | Path = ":memory:",
        policy: MemoryWritePolicy | None = None,
    ) -> None:
        self.path = str(path)
        self.policy = policy or MemoryWritePolicy()
        self.connection = sqlite3.connect(self.path, timeout=5.0)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA busy_timeout=5000")
        self.connection.execute("PRAGMA secure_delete=ON")
        self.connection.execute("PRAGMA journal_mode=DELETE")
        self._create_schema()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "SQLiteMemoryStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _create_schema(self) -> None:
        self.connection.executescript(SCHEMA_SQL)
        self.connection.commit()
        if self.schema_version > SCHEMA_VERSION:
            raise RuntimeError(
                f"database schema {self.schema_version} is newer than "
                f"supported {SCHEMA_VERSION}"
            )

    @property
    def schema_version(self) -> int:
        row = self.connection.execute(
            "SELECT schema_version FROM schema_metadata LIMIT 1"
        ).fetchone()
        return int(row[0])

    def integrity_check(self) -> bool:
        row = self.connection.execute("PRAGMA integrity_check").fetchone()
        return bool(row and row[0] == "ok")

    @property
    def audit_log(self) -> tuple[dict[str, str], ...]:
        rows = self.connection.execute(
            "SELECT action, memory_id, user_id, content_sha256, created_at "
            "FROM audit_events ORDER BY sequence"
        ).fetchall()
        return tuple(dict(row) for row in rows)

    def write(
        self, record: MemoryRecord
    ) -> tuple[MemoryRecord | None, PolicyDecision]:
        decision = self.policy.evaluate(record)
        if not decision.allowed:
            self._audit("reject", replace(record, status=MemoryStatus.REJECTED))
            return None, decision

        duplicate = self._find_duplicate(record)
        if duplicate is not None:
            self._audit("deduplicate", duplicate)
            return duplicate, PolicyDecision(True, ("deduplicated",))

        with self.connection:
            if record.supersedes:
                previous = self.get(record.supersedes)
                if previous is None or previous.user_id != record.user_id:
                    return None, PolicyDecision(
                        False, ("invalid_supersedes_reference",)
                    )
                self.connection.execute(
                    "UPDATE memories SET status=?, superseded_by=? WHERE id=?",
                    (MemoryStatus.SUPERSEDED.value, record.id, previous.id),
                )
                self.connection.execute(
                    "DELETE FROM search_index WHERE memory_id=?", (previous.id,)
                )
                record = replace(record, version=previous.version + 1)

            self.connection.execute(
                """
                INSERT INTO memories (
                    id, user_id, kind, memory_key, content, source_type, source_id,
                    source_location, user_confirmed, externally_verified, conflict,
                    sensitive, allow_long_term, provenance_metadata, created_at,
                    observed_at, valid_from, valid_until, last_confirmed_at,
                    supersedes, superseded_by, version, status, confidence, tags, project
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                to_values(record),
            )
            self.connection.execute(
                "INSERT INTO search_index(memory_id, user_id, search_text) "
                "VALUES (?,?,?)",
                (record.id, record.user_id, f"{record.key} {record.content}"),
            )
            self._audit("write", record, commit=False)
        return record, decision

    def get(self, memory_id: str) -> MemoryRecord | None:
        row = self.connection.execute(
            "SELECT * FROM memories WHERE id=?", (memory_id,)
        ).fetchone()
        return from_row(row) if row else None

    def active_for_user(
        self,
        user_id: str,
        at: datetime | None = None,
        *,
        enforce_temporal: bool = True,
    ) -> list[MemoryRecord]:
        at = at or datetime.now(timezone.utc)
        rows = self.connection.execute(
            "SELECT * FROM memories WHERE user_id=? AND status=?",
            (user_id, MemoryStatus.ACTIVE.value),
        ).fetchall()
        records = [from_row(row) for row in rows]
        if enforce_temporal:
            records = [record for record in records if record.is_valid_at(at)]
        return records

    def search(self, user_id: str, query: str) -> list[MemoryRecord]:
        pattern = f"%{query.casefold()}%"
        rows = self.connection.execute(
            """
            SELECT m.* FROM memories m
            JOIN search_index s ON s.memory_id=m.id
            WHERE s.user_id=? AND lower(s.search_text) LIKE ? AND m.status=?
            ORDER BY m.observed_at DESC
            """,
            (user_id, pattern, MemoryStatus.ACTIVE.value),
        ).fetchall()
        return [from_row(row) for row in rows]

    def forget(
        self, user_id: str, memory_id: str, *, compact: bool = True
    ) -> bool:
        record = self.get(memory_id)
        if record is None or record.user_id != user_id:
            return False
        digest = hashlib.sha256(record.content.encode("utf-8")).hexdigest()
        with self.connection:
            self.connection.execute(
                """
                UPDATE memories
                SET content='[deleted]', status=?, tags='[]', project=NULL
                WHERE id=? AND user_id=?
                """,
                (MemoryStatus.DELETED.value, memory_id, user_id),
            )
            self.connection.execute(
                "DELETE FROM search_index WHERE memory_id=?", (memory_id,)
            )
            self.connection.execute(
                "INSERT INTO audit_events("
                "action,memory_id,user_id,content_sha256,created_at"
                ") VALUES (?,?,?,?,?)",
                (
                    "delete",
                    memory_id,
                    user_id,
                    digest,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        if compact and self.path != ":memory:":
            self.connection.execute("VACUUM")
        return True

    def forget_key(
        self, user_id: str, key: str, *, compact: bool = True
    ) -> int:
        rows = self.connection.execute(
            "SELECT id FROM memories WHERE user_id=? AND memory_key=?",
            (user_id, key),
        ).fetchall()
        count = sum(
            self.forget(user_id, row["id"], compact=False) for row in rows
        )
        if count and compact and self.path != ":memory:":
            self.connection.execute("VACUUM")
        return count

    def _find_duplicate(
        self, candidate: MemoryRecord
    ) -> MemoryRecord | None:
        rows = self.connection.execute(
            "SELECT * FROM memories WHERE "
            "user_id=? AND kind=? AND memory_key=? AND status=?",
            (
                candidate.user_id,
                candidate.kind.value,
                candidate.key,
                MemoryStatus.ACTIVE.value,
            ),
        ).fetchall()
        wanted = normalise(candidate.content)
        for row in rows:
            record = from_row(row)
            if normalise(record.content) == wanted:
                return record
        return None

    def _audit(
        self,
        action: str,
        record: MemoryRecord,
        *,
        commit: bool = True,
    ) -> None:
        digest = hashlib.sha256(record.content.encode("utf-8")).hexdigest()
        self.connection.execute(
            "INSERT INTO audit_events("
            "action,memory_id,user_id,content_sha256,created_at"
            ") VALUES (?,?,?,?,?)",
            (
                action,
                record.id,
                record.user_id,
                digest,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        if commit:
            self.connection.commit()
