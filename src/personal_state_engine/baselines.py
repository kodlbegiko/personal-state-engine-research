from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .retrieval import cosine_similarity


@dataclass(slots=True)
class Fact:
    user_id: str
    key: str
    value: str
    observed_at: datetime
    valid_until: datetime | None = None
    source: str = "user"
    deleted: bool = False
    trusted: bool = True


class BaselineSystem:
    code = "base"
    supports_proactive = False
    supports_verification = False

    def remember(self, fact: Fact) -> None:
        raise NotImplementedError

    def recall(self, user_id: str, key: str, at: datetime) -> str | None:
        raise NotImplementedError

    def forget(self, user_id: str, key: str) -> None:
        pass

    def should_remind(self, *, due_hours: float, completed: bool) -> bool:
        return False

    def verify_completion(self, *, tool_success: bool, evidence: bool, effect_matches: bool) -> bool:
        return tool_success


class NoMemory(BaselineSystem):
    code = "B0"

    def remember(self, fact: Fact) -> None:
        return None

    def recall(self, user_id: str, key: str, at: datetime) -> str | None:
        return None


class FullReplay(BaselineSystem):
    code = "B1"

    def __init__(self, context_limit: int = 8) -> None:
        self.history: list[Fact] = []
        self.context_limit = context_limit

    def remember(self, fact: Fact) -> None:
        self.history.append(fact)

    def recall(self, user_id: str, key: str, at: datetime) -> str | None:
        # Simulates finite context: only the tail is available. No user isolation.
        for fact in reversed(self.history[-self.context_limit :]):
            if fact.key == key and not fact.deleted:
                return fact.value
        return None


class RollingSummary(BaselineSystem):
    code = "B2"

    def __init__(self) -> None:
        self.summary: dict[str, Fact] = {}

    def remember(self, fact: Fact) -> None:
        # Deliberately loses provenance, user identity and version history.
        self.summary[fact.key] = fact

    def recall(self, user_id: str, key: str, at: datetime) -> str | None:
        fact = self.summary.get(key)
        return None if fact is None or fact.deleted else fact.value

    def forget(self, user_id: str, key: str) -> None:
        self.summary.pop(key, None)


class NaiveRAG(BaselineSystem):
    code = "B3"

    def __init__(self) -> None:
        self.documents: list[Fact] = []

    def remember(self, fact: Fact) -> None:
        self.documents.append(fact)

    def recall(self, user_id: str, key: str, at: datetime) -> str | None:
        candidates = [fact for fact in self.documents if not fact.deleted]
        if not candidates:
            return None
        # Similarity-only retrieval, with oldest-first tie breaking.
        ranked = sorted(
            enumerate(candidates),
            key=lambda pair: (cosine_similarity(pair[1].key, key), -pair[0]),
            reverse=True,
        )
        return ranked[0][1].value


class StructuredMemory(BaselineSystem):
    code = "B4"

    def __init__(self) -> None:
        self.current: dict[tuple[str, str], Fact] = {}

    def remember(self, fact: Fact) -> None:
        if not fact.trusted:
            return
        self.current[(fact.user_id, fact.key)] = fact

    def recall(self, user_id: str, key: str, at: datetime) -> str | None:
        fact = self.current.get((user_id, key))
        return None if fact is None or fact.deleted else fact.value

    def forget(self, user_id: str, key: str) -> None:
        self.current.pop((user_id, key), None)


class TemporalMemory(StructuredMemory):
    code = "B5"

    def recall(self, user_id: str, key: str, at: datetime) -> str | None:
        fact = self.current.get((user_id, key))
        if fact is None or fact.deleted:
            return None
        if fact.valid_until is not None and at >= fact.valid_until:
            return None
        return fact.value


class CommitmentAssistant(TemporalMemory):
    code = "B6"
    supports_proactive = True

    def should_remind(self, *, due_hours: float, completed: bool) -> bool:
        return not completed and due_hours <= 72


class VerifiedAssistant(CommitmentAssistant):
    code = "B7"
    supports_verification = True

    def verify_completion(self, *, tool_success: bool, evidence: bool, effect_matches: bool) -> bool:
        return tool_success and evidence and effect_matches


BASELINES: tuple[type[BaselineSystem], ...] = (
    NoMemory,
    FullReplay,
    RollingSummary,
    NaiveRAG,
    StructuredMemory,
    TemporalMemory,
    CommitmentAssistant,
    VerifiedAssistant,
)
