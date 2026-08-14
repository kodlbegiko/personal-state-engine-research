from __future__ import annotations

from datetime import datetime, timezone

from .models import Commitment, CommitmentStatus, InterventionDecision, Priority


class ProactiveController:
    def decide(
        self,
        commitment: Commitment,
        *,
        now: datetime | None = None,
        user_busy: bool = False,
        already_reminded: bool = False,
        ai_confidence: float = 1.0,
    ) -> InterventionDecision:
        now = now or datetime.now(timezone.utc)
        terminal = {
            CommitmentStatus.COMPLETED,
            CommitmentStatus.CANCELLED,
            CommitmentStatus.SUPERSEDED,
            CommitmentStatus.EXPIRED,
        }
        if commitment.status in terminal:
            return InterventionDecision(False, "silent", 0.0, ("terminal_status",))
        if already_reminded:
            return InterventionDecision(False, "silent", 0.0, ("duplicate_suppression",))
        if ai_confidence < 0.55:
            return InterventionDecision(False, "silent", 0.0, ("insufficient_confidence",))

        priority = commitment.priority.value / Priority.CRITICAL.value
        urgency = 0.0
        reasons: list[str] = []
        if commitment.due_at is not None:
            hours = (commitment.due_at - now).total_seconds() / 3600
            if hours <= 0:
                urgency = 1.0
                reasons.append("overdue")
            elif hours <= 24:
                urgency = 0.9
                reasons.append("due_within_24h")
            elif hours <= 72:
                urgency = 0.6
                reasons.append("due_within_72h")
            elif hours <= 168:
                urgency = 0.3
        burden = 0.25 if user_busy else 0.0
        score = (
            0.35 * priority
            + 0.35 * urgency
            + 0.20 * max(0.0, min(1.0, commitment.expected_loss))
            + 0.10 * ai_confidence
            - burden
        )
        score = round(max(0.0, min(1.0, score)), 6)
        if score < 0.58:
            return InterventionDecision(False, "silent", score, tuple(reasons + ["below_threshold"]))
        if commitment.action_risk >= 0.5:
            return InterventionDecision(True, "ask_confirmation", score, tuple(reasons + ["high_action_risk"]))
        return InterventionDecision(True, "notify", score, tuple(reasons + ["actionable"]))
