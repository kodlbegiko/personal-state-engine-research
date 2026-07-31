from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryKind(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class SourceType(str, Enum):
    USER_CONFIRMED = "user_confirmed"
    EXTERNALLY_VERIFIED = "externally_verified"
    MODEL_INFERRED = "model_inferred"
    SYSTEM_GENERATED = "system_generated"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    DELETED = "deleted"
    REJECTED = "rejected"


class CommitmentStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    WAITING = "waiting"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"


class Priority(int, Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass(slots=True)
class Provenance:
    source_type: SourceType
    source_id: str
    source_location: str | None = None
    user_confirmed: bool = False
    externally_verified: bool = False
    conflict: bool = False
    sensitive: bool = False
    allow_long_term: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MemoryRecord:
    user_id: str
    kind: MemoryKind
    key: str
    content: str
    provenance: Provenance
    created_at: datetime = field(default_factory=utc_now)
    observed_at: datetime = field(default_factory=utc_now)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    last_confirmed_at: datetime | None = None
    supersedes: str | None = None
    superseded_by: str | None = None
    version: int = 1
    status: MemoryStatus = MemoryStatus.ACTIVE
    confidence: float = 1.0
    tags: tuple[str, ...] = ()
    project: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))

    def is_valid_at(self, at: datetime) -> bool:
        if self.status is not MemoryStatus.ACTIVE:
            return False
        if self.valid_from is not None and at < self.valid_from:
            return False
        if self.valid_until is not None and at >= self.valid_until:
            return False
        return True


@dataclass(slots=True)
class Commitment:
    user_id: str
    title: str
    description: str
    owner: str
    due_at: datetime | None = None
    status: CommitmentStatus = CommitmentStatus.PLANNED
    priority: Priority = Priority.MEDIUM
    dependencies: tuple[str, ...] = ()
    blocking_reason: str | None = None
    completion_evidence: str | None = None
    cancelled_reason: str | None = None
    superseded_by: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    last_checked_at: datetime | None = None
    expected_loss: float = 0.5
    action_risk: float = 0.0
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(slots=True)
class RetrievalResult:
    memory: MemoryRecord
    score: float
    reasons: tuple[str, ...]


@dataclass(slots=True)
class InterventionDecision:
    should_intervene: bool
    action: str
    score: float
    reasons: tuple[str, ...]


@dataclass(slots=True)
class VerificationResult:
    verified: bool
    false_completion: bool
    reasons: tuple[str, ...]
