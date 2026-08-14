from __future__ import annotations

import unittest

from personal_state_engine.verification import ActionResult, VerificationLoop


class TrustedVerificationTests(unittest.TestCase):
    def test_strict_mode_rejects_tool_self_report(self):
        result = VerificationLoop(require_trusted_evidence=True).verify(
            ActionResult(True, True, "tool said done", "exists", "exists", evidence_source="tool_self_report")
        )
        self.assertFalse(result.verified)
        self.assertIn("untrusted_completion_evidence", result.reasons)

    def test_strict_mode_accepts_external_observer(self):
        result = VerificationLoop(require_trusted_evidence=True).verify(
            ActionResult(
                True,
                True,
                "observed file",
                "exists",
                "exists",
                evidence_source="filesystem_observer",
                evidence_digest="a" * 64,
            )
        )
        self.assertTrue(result.verified)

    def test_invalid_digest_rejected(self):
        result = VerificationLoop().verify(
            ActionResult(True, True, "evidence", "ok", "ok", evidence_digest="not-a-sha")
        )
        self.assertFalse(result.verified)
        self.assertIn("invalid_evidence_digest", result.reasons)


if __name__ == "__main__":
    unittest.main()
