from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from personal_state_engine.commitments import CommitmentLedger
from personal_state_engine.models import Commitment, CommitmentStatus, Priority
from personal_state_engine.proactive import ProactiveController

UTC = timezone.utc


class CommitmentTests(unittest.TestCase):
    def make(self, **kwargs):
        data = {
            "user_id": "u1",
            "title": "Submit report",
            "description": "Submit reproducibility report",
            "owner": "u1",
            "status": CommitmentStatus.ACTIVE,
            "priority": Priority.HIGH,
            "due_at": datetime(2026, 1, 2, tzinfo=UTC),
            "expected_loss": 0.9,
        }
        data.update(kwargs)
        return Commitment(**data)

    def test_completion_requires_evidence(self):
        ledger = CommitmentLedger()
        item = ledger.add(self.make())
        with self.assertRaises(ValueError):
            ledger.transition("u1", item.id, CommitmentStatus.COMPLETED)

    def test_completion_with_evidence(self):
        ledger = CommitmentLedger()
        item = ledger.add(self.make())
        updated = ledger.transition("u1", item.id, CommitmentStatus.COMPLETED, evidence="artifact-sha")
        self.assertEqual(updated.status, CommitmentStatus.COMPLETED)
        self.assertEqual(updated.completion_evidence, "artifact-sha")

    def test_invalid_state_transition_rejected(self):
        ledger = CommitmentLedger()
        item = ledger.add(self.make(status=CommitmentStatus.COMPLETED, completion_evidence="proof"))
        with self.assertRaises(ValueError):
            ledger.transition("u1", item.id, CommitmentStatus.ACTIVE)

    def test_cross_user_transition_rejected(self):
        ledger = CommitmentLedger()
        item = ledger.add(self.make())
        with self.assertRaises(PermissionError):
            ledger.transition("u2", item.id, CommitmentStatus.CANCELLED, reason="not mine")

    def test_critical_due_item_triggers_intervention(self):
        now = datetime(2026, 1, 1, tzinfo=UTC)
        decision = ProactiveController().decide(self.make(due_at=now + timedelta(hours=12)), now=now)
        self.assertTrue(decision.should_intervene)
        self.assertEqual(decision.action, "notify")

    def test_completed_item_stays_silent(self):
        decision = ProactiveController().decide(
            self.make(status=CommitmentStatus.COMPLETED, completion_evidence="proof")
        )
        self.assertFalse(decision.should_intervene)

    def test_duplicate_reminder_suppressed(self):
        decision = ProactiveController().decide(self.make(), already_reminded=True)
        self.assertFalse(decision.should_intervene)
        self.assertIn("duplicate_suppression", decision.reasons)

    def test_high_risk_action_requires_confirmation(self):
        now = datetime(2026, 1, 1, tzinfo=UTC)
        decision = ProactiveController().decide(
            self.make(due_at=now + timedelta(hours=2), action_risk=0.8),
            now=now,
        )
        self.assertEqual(decision.action, "ask_confirmation")


if __name__ == "__main__":
    unittest.main()
