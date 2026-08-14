from __future__ import annotations

import unittest

from personal_state_engine.recovery import RecoveryAction, RecoveryExecutor
from personal_state_engine.verification import ActionResult


def result(*, success=True, evidence="proof", expected="ok", observed="ok"):
    return ActionResult(True, success, evidence, expected, observed)


class RecoveryTests(unittest.TestCase):
    def test_first_verified_action_completes(self):
        report = RecoveryExecutor().run([RecoveryAction("primary", lambda: result())])
        self.assertEqual(report.status, "completed")
        self.assertEqual(report.selected_action, "primary")

    def test_false_completion_rolls_back_then_uses_alternative(self):
        calls: list[str] = []

        def primary():
            calls.append("primary")
            return result(evidence=None, observed="missing")

        def rollback():
            calls.append("rollback")
            return result(expected="absent", observed="absent")

        def alternative():
            calls.append("alternative")
            return result()

        report = RecoveryExecutor().run(
            [
                RecoveryAction("primary", primary, rollback),
                RecoveryAction("alternative", alternative),
            ]
        )
        self.assertEqual(report.status, "completed")
        self.assertEqual(report.selected_action, "alternative")
        self.assertEqual(calls, ["primary", "rollback", "alternative"])
        self.assertTrue(report.attempts[0].rollback_verified)

    def test_unverified_rollback_blocks_further_actions(self):
        alternative_called = False

        def alternative():
            nonlocal alternative_called
            alternative_called = True
            return result()

        report = RecoveryExecutor().run(
            [
                RecoveryAction(
                    "primary",
                    lambda: result(evidence=None, observed="partial"),
                    lambda: result(evidence=None, expected="absent", observed="present"),
                ),
                RecoveryAction("alternative", alternative),
            ]
        )
        self.assertEqual(report.status, "blocked")
        self.assertFalse(alternative_called)

    def test_all_clean_failures_end_failed(self):
        report = RecoveryExecutor().run(
            [
                RecoveryAction("one", lambda: result(success=False, evidence=None, observed=None)),
                RecoveryAction("two", lambda: result(success=False, evidence=None, observed=None)),
            ]
        )
        self.assertEqual(report.status, "failed")
        self.assertEqual(len(report.attempts), 2)


if __name__ == "__main__":
    unittest.main()
