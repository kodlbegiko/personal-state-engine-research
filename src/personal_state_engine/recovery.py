from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .verification import ActionResult, VerificationLoop


@dataclass(frozen=True, slots=True)
class RecoveryAction:
    name: str
    execute: Callable[[], ActionResult]
    rollback: Callable[[], ActionResult] | None = None


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    action: str
    verified: bool
    false_completion: bool
    reasons: tuple[str, ...]
    rollback_attempted: bool = False
    rollback_verified: bool | None = None


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    status: str
    selected_action: str | None
    attempts: tuple[AttemptRecord, ...]


class RecoveryExecutor:
    """Execute alternatives without compounding unverified side effects."""

    def __init__(self, verifier: VerificationLoop | None = None) -> None:
        self.verifier = verifier or VerificationLoop()

    def run(self, actions: Iterable[RecoveryAction]) -> RecoveryReport:
        records: list[AttemptRecord] = []
        for action in actions:
            result = action.execute()
            verification = self.verifier.verify(result)
            if verification.verified:
                records.append(
                    AttemptRecord(action.name, True, False, verification.reasons)
                )
                return RecoveryReport("completed", action.name, tuple(records))

            rollback_attempted = False
            rollback_verified: bool | None = None
            if result.tool_success and action.rollback is not None:
                rollback_attempted = True
                rollback_result = action.rollback()
                rollback_verification = self.verifier.verify(rollback_result)
                rollback_verified = rollback_verification.verified
                if not rollback_verified:
                    records.append(
                        AttemptRecord(
                            action.name,
                            False,
                            verification.false_completion,
                            verification.reasons + ("rollback_unverified",),
                            True,
                            False,
                        )
                    )
                    return RecoveryReport("blocked", None, tuple(records))

            records.append(
                AttemptRecord(
                    action.name,
                    False,
                    verification.false_completion,
                    verification.reasons,
                    rollback_attempted,
                    rollback_verified,
                )
            )
        return RecoveryReport("failed", None, tuple(records))
