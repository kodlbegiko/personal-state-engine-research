from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from personal_state_engine.models import MemoryKind, MemoryRecord, MemoryStatus, Provenance, SourceType
from personal_state_engine.store import MemoryStore

UTC = timezone.utc


def memory(**overrides):
    data = {
        "user_id": "u1",
        "kind": MemoryKind.SEMANTIC,
        "key": "preferred_editor",
        "content": "VS Code",
        "provenance": Provenance(SourceType.USER_CONFIRMED, "msg-1", user_confirmed=True),
        "observed_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    data.update(overrides)
    return MemoryRecord(**data)


class MemoryStoreTests(unittest.TestCase):
    def test_writes_allowed_memory(self):
        store = MemoryStore()
        stored, decision = store.write(memory())
        self.assertTrue(decision.allowed)
        self.assertIsNotNone(stored)

    def test_deduplicates_normalized_content(self):
        store = MemoryStore()
        first, _ = store.write(memory(content="VS   Code"))
        second, decision = store.write(memory(content="vs code"))
        self.assertEqual(first.id, second.id)
        self.assertEqual(decision.reasons, ("deduplicated",))

    def test_supersedes_old_memory(self):
        store = MemoryStore()
        old, _ = store.write(memory(content="vim"))
        new, decision = store.write(memory(content="vscode", supersedes=old.id))
        self.assertTrue(decision.allowed)
        self.assertEqual(store.get(old.id).status, MemoryStatus.SUPERSEDED)
        self.assertEqual(store.get(old.id).superseded_by, new.id)
        self.assertEqual(new.version, 2)

    def test_rejects_cross_user_supersedes(self):
        store = MemoryStore()
        old, _ = store.write(memory(user_id="u2"))
        new, decision = store.write(memory(user_id="u1", supersedes=old.id))
        self.assertIsNone(new)
        self.assertIn("invalid_supersedes_reference", decision.reasons)

    def test_forget_removes_content_from_retrieval(self):
        store = MemoryStore()
        stored, _ = store.write(memory(content="private"))
        self.assertTrue(store.forget("u1", stored.id))
        self.assertEqual(store.active_for_user("u1"), [])
        self.assertEqual(store.get(stored.id).content, "[deleted]")

    def test_forget_is_user_scoped(self):
        store = MemoryStore()
        stored, _ = store.write(memory(user_id="u2"))
        self.assertFalse(store.forget("u1", stored.id))
        self.assertEqual(len(store.active_for_user("u2")), 1)

    def test_temporal_validity(self):
        store = MemoryStore()
        start = datetime(2026, 1, 1, tzinfo=UTC)
        stored, _ = store.write(memory(valid_from=start, valid_until=start + timedelta(days=1)))
        self.assertIn(stored, store.active_for_user("u1", start + timedelta(hours=1)))
        self.assertNotIn(stored, store.active_for_user("u1", start + timedelta(days=2)))

    def test_audit_log_does_not_store_plaintext(self):
        store = MemoryStore()
        store.write(memory(content="highly private note"))
        event = store.audit_log[-1]
        self.assertNotIn("highly private note", event.values())
        self.assertEqual(len(event["content_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
