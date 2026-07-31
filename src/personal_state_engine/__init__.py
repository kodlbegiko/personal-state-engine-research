"""Personal State Engine research prototype."""

from .engine import PersonalStateEngine
from .persistence import SQLiteMemoryStore
from .recovery import RecoveryAction, RecoveryExecutor
from .experiment_records import TrialRecord
from .scoring import StructuredOutcomeScorer
from .models import (
    Commitment,
    CommitmentStatus,
    MemoryKind,
    MemoryRecord,
    MemoryStatus,
    Priority,
    Provenance,
    SourceType,
)

__all__ = [
    "PersonalStateEngine",
    "SQLiteMemoryStore",
    "RecoveryAction",
    "RecoveryExecutor",
    "TrialRecord",
    "StructuredOutcomeScorer",
    "Commitment",
    "CommitmentStatus",
    "MemoryKind",
    "MemoryRecord",
    "MemoryStatus",
    "Priority",
    "Provenance",
    "SourceType",
]

__version__ = "0.1.0"
