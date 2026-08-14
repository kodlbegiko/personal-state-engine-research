from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone

from .models import MemoryRecord, RetrievalResult, SourceType
from .store import MemoryStore

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def tokens(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN_RE.findall(text)]


def cosine_similarity(left: str, right: str) -> float:
    a, b = Counter(tokens(left)), Counter(tokens(right))
    if not a or not b:
        return 0.0
    numerator = sum(a[key] * b.get(key, 0) for key in a)
    denominator = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(
        sum(v * v for v in b.values())
    )
    return numerator / denominator if denominator else 0.0


_SOURCE_TRUST = {
    SourceType.USER_CONFIRMED: 1.0,
    SourceType.EXTERNALLY_VERIFIED: 1.0,
    SourceType.SYSTEM_GENERATED: 0.7,
    SourceType.MODEL_INFERRED: 0.3,
}


class RetrievalController:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def retrieve(
        self,
        *,
        user_id: str,
        query: str,
        at: datetime | None = None,
        goal_tags: tuple[str, ...] = (),
        project: str | None = None,
        token_budget: int = 512,
        enforce_temporal: bool = True,
    ) -> list[RetrievalResult]:
        at = at or datetime.now(timezone.utc)
        candidates = self.store.active_for_user(
            user_id,
            at,
            enforce_temporal=enforce_temporal,
        )
        scored = [
            self._score(record, query, at, goal_tags=goal_tags, project=project)
            for record in candidates
        ]
        scored.sort(key=lambda item: (item.score, item.memory.observed_at), reverse=True)

        selected: list[RetrievalResult] = []
        used = 0
        for result in scored:
            estimated_tokens = max(1, len(result.memory.content) // 4)
            if used + estimated_tokens > token_budget:
                continue
            if result.score <= 0.0:
                continue
            selected.append(result)
            used += estimated_tokens
        return selected

    def _score(
        self,
        record: MemoryRecord,
        query: str,
        at: datetime,
        *,
        goal_tags: tuple[str, ...],
        project: str | None,
    ) -> RetrievalResult:
        reasons: list[str] = []
        similarity = cosine_similarity(f"{record.key} {record.content}", query)
        if similarity:
            reasons.append("semantic_overlap")
        tag_overlap = len(set(goal_tags).intersection(record.tags))
        if tag_overlap:
            reasons.append("goal_tag_match")
        project_match = 1.0 if project and record.project == project else 0.0
        if project_match:
            reasons.append("project_match")
        source_trust = _SOURCE_TRUST[record.provenance.source_type]
        age_days = max(0.0, (at - record.observed_at).total_seconds() / 86400)
        recency = 1.0 / (1.0 + age_days / 30.0)
        confidence = min(1.0, max(0.0, record.confidence))
        score = (
            0.45 * similarity
            + 0.15 * min(tag_overlap, 1)
            + 0.10 * project_match
            + 0.12 * source_trust
            + 0.10 * recency
            + 0.08 * confidence
        )
        return RetrievalResult(record, round(score, 6), tuple(reasons))
