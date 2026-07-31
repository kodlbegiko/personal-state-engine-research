from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from personal_state_engine.models import MemoryKind, MemoryRecord, Provenance, SourceType
from personal_state_engine.retrieval import RetrievalController
from personal_state_engine.store import MemoryStore

UTC = timezone.utc


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.retrieval = RetrievalController(self.store)

    def add(self, key, content, *, user="u1", observed=None, valid_until=None, tags=(), project=None, confidence=1.0):
        record = MemoryRecord(
            user_id=user,
            kind=MemoryKind.SEMANTIC,
            key=key,
            content=content,
            provenance=Provenance(SourceType.USER_CONFIRMED, key, user_confirmed=True),
            observed_at=observed or datetime(2026, 1, 1, tzinfo=UTC),
            valid_until=valid_until,
            tags=tags,
            project=project,
            confidence=confidence,
        )
        return self.store.write(record)[0]

    def test_user_isolation(self):
        self.add("city", "Taipei", user="u1")
        self.add("city", "Kaohsiung", user="u2")
        results = self.retrieval.retrieve(user_id="u1", query="city", at=datetime(2026, 1, 2, tzinfo=UTC))
        self.assertEqual([item.memory.content for item in results], ["Taipei"])

    def test_temporal_filter_excludes_expired(self):
        start = datetime(2026, 1, 1, tzinfo=UTC)
        self.add("schedule", "night work", valid_until=start + timedelta(days=1))
        results = self.retrieval.retrieve(user_id="u1", query="schedule", at=start + timedelta(days=2))
        self.assertEqual(results, [])

    def test_goal_and_project_raise_relevance(self):
        self.add("constraint", "keep benchmark immutable", tags=("research",), project="pse")
        self.add("constraint", "buy groceries", tags=("home",), project="life")
        results = self.retrieval.retrieve(
            user_id="u1",
            query="constraint",
            at=datetime(2026, 1, 2, tzinfo=UTC),
            goal_tags=("research",),
            project="pse",
        )
        self.assertEqual(results[0].memory.content, "keep benchmark immutable")

    def test_token_budget_is_enforced(self):
        self.add("alpha", "a" * 80)
        self.add("beta", "b" * 80)
        results = self.retrieval.retrieve(
            user_id="u1",
            query="alpha beta",
            at=datetime(2026, 1, 2, tzinfo=UTC),
            token_budget=20,
        )
        self.assertLessEqual(sum(max(1, len(item.memory.content) // 4) for item in results), 20)


if __name__ == "__main__":
    unittest.main()
