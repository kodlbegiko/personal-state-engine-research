from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from .models import Commitment, CommitmentStatus


_ALLOWED_TRANSITIONS: dict[CommitmentStatus, set[CommitmentStatus]] = {
    CommitmentStatus.PLANNED: {
        CommitmentStatus.ACTIVE,
        CommitmentStatus.CANCELLED,
        CommitmentStatus.SUPERSEDED,
    },
    CommitmentStatus.ACTIVE: {
        CommitmentStatus.WAITING,
        CommitmentStatus.BLOCKED,
        CommitmentStatus.COMPLETED,
        CommitmentStatus.CANCELLED,
        CommitmentStatus.SUPERSEDED,
        CommitmentStatus.EXPIRED,
    },
    CommitmentStatus.WAITING: {
        CommitmentStatus.ACTIVE,
        CommitmentStatus.BLOCKED,
        CommitmentStatus.COMPLETED,
        CommitmentStatus.CANCELLED,
        CommitmentStatus.EXPIRED,
    },
    CommitmentStatus.BLOCKED: {
        CommitmentStatus.ACTIVE,
        CommitmentStatus.CANCELLED,
        CommitmentStatus.EXPIRED,
    },
    CommitmentStatus.COMPLETED: set(),
    CommitmentStatus.CANCELLED: set(),
    CommitmentStatus.SUPERSEDED: set(),
    CommitmentStatus.EXPIRED: set(),
}


class CommitmentLedger:
    def __init__(self) -> None:
        self._items: dict[str, Commitment] = {}

    def add(self, commitment: Commitment) -> Commitment:
        if commitment.id in self._items:
            raise ValueError("duplicate commitment id")
        self._items[commitment.id] = commitment
        return commitment

    def get(self, commitment_id: str) -> Commitment | None:
        return self._items.get(commitment_id)

    def transition(
        self,
        user_id: str,
        commitment_id: str,
        new_status: CommitmentStatus,
        *,
        evidence: str | None = None,
        reason: str | None = None,
        superseded_by: str | None = None,
    ) -> Commitment:
        current = self._items[commitment_id]
        if current.user_id != user_id:
            raise PermissionError("cross-user commitment access")
        if new_status not in _ALLOWED_TRANSITIONS[current.status]:
            raise ValueError(f"invalid transition: {current.status.value} -> {new_status.value}")
        if new_status is CommitmentStatus.COMPLETED and not evidence:
            raise ValueError("completion evidence is required")
        if new_status is CommitmentStatus.CANCELLED and not reason:
            raise ValueError("cancellation reason is required")
        updated = replace(
            current,
            status=new_status,
            completion_evidence=evidence or current.completion_evidence,
            cancelled_reason=reason or current.cancelled_reason,
            superseded_by=superseded_by or current.superseded_by,
            last_checked_at=datetime.now(timezone.utc),
        )
        self._items[commitment_id] = updated
        return updated

    def pending(self, user_id: str) -> list[Commitment]:
        terminal = {
            CommitmentStatus.COMPLETED,
            CommitmentStatus.CANCELLED,
            CommitmentStatus.SUPERSEDED,
            CommitmentStatus.EXPIRED,
        }
        return [
            item
            for item in self._items.values()
            if item.user_id == user_id and item.status not in terminal
        ]
