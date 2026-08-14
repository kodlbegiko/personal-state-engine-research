from __future__ import annotations

import re
from dataclasses import dataclass

from .models import VerificationResult

_SHA256 = re.compile(r"^[0-9a-f]{64}$", re.I)


@dataclass(slots=True)
class ActionResult:
    attempted: bool
    tool_success: bool
    evidence: str | None
    expected_effect: str | None
    observed_effect: str | None
    evidence_source: str | None = None
    evidence_digest: str | None = None


class VerificationLoop:
    def __init__(
        self,
        *,
        require_trusted_evidence: bool = False,
        trusted_evidence_sources: frozenset[str] | None = None,
    ) -> None:
        self.require_trusted_evidence = require_trusted_evidence
        self.trusted_evidence_sources = trusted_evidence_sources or frozenset(
            {"external_observer", "repository_state", "filesystem_observer", "database_query"}
        )

    def verify(self, result: ActionResult) -> VerificationResult:
        reasons: list[str] = []
        if not result.attempted:
            reasons.append("action_not_attempted")
        if not result.tool_success:
            reasons.append("tool_reported_failure")
        if not result.evidence:
            reasons.append("missing_completion_evidence")
        elif self.require_trusted_evidence and result.evidence_source not in self.trusted_evidence_sources:
            reasons.append("untrusted_completion_evidence")
        if result.evidence_digest is not None and not _SHA256.fullmatch(result.evidence_digest):
            reasons.append("invalid_evidence_digest")
        if result.expected_effect is None or result.observed_effect is None:
            reasons.append("effect_not_observed")
        elif result.expected_effect != result.observed_effect:
            reasons.append("observed_effect_mismatch")
        verified = not reasons
        false_completion = result.tool_success and not verified
        return VerificationResult(verified, false_completion, tuple(reasons))
