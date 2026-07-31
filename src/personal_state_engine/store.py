from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime, timezone

from .models import MemoryRecord, MemoryStatus
from .policy import MemoryWritePolicy, PolicyDecision


def _normalise(value: str) -> str:
    return " ".join(value.casefold().split())


class MemoryStore:
    def __init__(self, policy: MemoryWritePolicy | None = None) -> None:
        self._records: dict[str, MemoryRecord] = {}
        self._audit: list[dict[str, str]] = []
        self.policy = policy or MemoryWritePolicy()

    @property
    def audit_log(self) -> tuple[dict[str, str], ...]:
        return tuple(self._audit)

    def write(self, record: MemoryRecord) -> tuple[MemoryRecord | None, PolicyDecision]:
        decision = self.policy.evaluate(record)
        if not decision.allowed:
            rejected = replace(record, status=MemoryStatus.REJECTED)
            self._audit_event("reject", rejected)
            return None, decision

        duplicate = self._find_duplicate(record)
        if duplicate is not None:
            self._audit_event("deduplicate", duplicate)
            return duplicate, PolicyDecision(True, ("deduplicated",))

        if record.supersedes:
            previous = self._records.get(record.supersedes)
            if previous is None or previous.user_id != record.user_id:
                return None, PolicyDecision(False, ("invalid_supersedes_reference",))
            updated_previous = replace(
                previous,
                status=MemoryStatus.SUPERSEDED,
                superseded_by=record.id,
            )
            self._records[previous.id] = updated_previous
            record = replace(record, version=previous.version + 1)

        self._records[record.id] = record
        self._audit_event("write", record)
        return record, decision

    def get(self, memory_id: str) -> MemoryRecord | None:
        return self._records.get(memory_id)

    def active_for_user(
        self,
        user_id: str,
        at: datetime | None = None,
        *,
        enforce_temporal: bool = True,
    ) -> list[MemoryRecord]:
        at = at or datetime.now(timezone.utc)
        records = [r for r in self._records.values() if r.user_id == user_id]
        if enforce_temporal:
            return [r for r in records if r.is_valid_at(at)]
        return [r for r in records if r.status is MemoryStatus.ACTIVE]

    def forget(self, user_id: str, memory_id: str) -> bool:
        record = self._records.get(memory_id)
        if record is None or record.user_id != user_id:
            return False
        tombstone = replace(
            record,
            content="[deleted]",
            status=MemoryStatus.DELETED,
            tags=(),
            project=None,
        )
        self._records[memory_id] = tombstone
        self._audit_event("delete", tombstone)
        return True

    def forget_key(self, user_id: str, key: str) -> int:
        ids = [
            record.id
            for record in self._records.values()
            if record.user_id == user_id and record.key == key
        ]
        return sum(self.forget(user_id, memory_id) for memory_id in ids)

    def _find_duplicate(self, candidate: MemoryRecord) -> MemoryRecord | None:
        candidate_content = _normalise(candidate.content)
        for record in self._records.values():
            if (
                record.user_id == candidate.user_id
                and record.kind == candidate.kind
                and record.key == candidate.key
                and record.status is MemoryStatus.ACTIVE
                and _normalise(record.content) == candidate_content
            ):
                return record
        return None

    def _audit_event(self, action: str, record: MemoryRecord) -> None:
        digest = hashlib.sha256(record.content.encode("utf-8")).hexdigest()
        self._audit.append(
            {
                "action": action,
                "memory_id": record.id,
                "user_id": record.user_id,
                "content_sha256": digest,
                "status": record.status.value,
            }
        )
