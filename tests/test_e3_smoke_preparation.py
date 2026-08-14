from __future__ import annotations

import importlib.util
import unittest
from dataclasses import dataclass
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "run_longmemeval_e3_smoke.py"
SPEC = importlib.util.spec_from_file_location("e3_smoke", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@dataclass(frozen=True)
class Turn:
    role: str
    content: str
    has_answer: bool = False


@dataclass(frozen=True)
class Session:
    session_id: str
    timestamp: str
    turns: tuple[Turn, ...]


@dataclass(frozen=True)
class Example:
    question_id: str
    question_type: str
    question: str
    answer: object
    question_date: str
    sessions: tuple[Session, ...]
    answer_session_ids: tuple[str, ...]

    @property
    def is_abstention(self) -> bool:
        return self.question_id.endswith("_abs")


def example(question_id: str, question_type: str, history: str) -> Example:
    return Example(
        question_id=question_id,
        question_type=question_type,
        question="What did I say?",
        answer=history,
        question_date="2026-01-02",
        sessions=(
            Session(
                "s-" + history,
                "2026-01-01",
                (Turn("user", history),),
            ),
        ),
        answer_session_ids=("s-" + history,),
    )


class E3SmokePreparationTests(unittest.TestCase):
    def rows(self):
        rows = []
        kinds = [
            "single-session-user",
            "single-session-assistant",
            "single-session-preference",
            "multi-session",
            "temporal-reasoning",
            "knowledge-update",
        ]
        for index in range(24):
            rows.append(
                example(
                    f"q{index}",
                    kinds[index % len(kinds)],
                    f"history-{index // 2}",
                )
            )
        rows.append(example("q_abs", "multi-session", "unknown-history"))
        return rows

    def test_splits_are_deterministic_and_history_isolated(self):
        first = MODULE.build_grouped_stratified_splits(self.rows(), "seed-v1")
        second = MODULE.build_grouped_stratified_splits(self.rows(), "seed-v1")
        self.assertEqual(
            {key: [row.question_id for row in value] for key, value in first.items()},
            {key: [row.question_id for row in value] for key, value in second.items()},
        )
        MODULE.assert_no_history_leakage(first)
        self.assertTrue(all(first[split] for split in MODULE._SPLIT_ORDER))

    def test_smoke_selection_covers_distinct_categories_when_available(self):
        selected = MODULE.select_smoke_cases(self.rows(), 4)
        self.assertEqual(len(selected), 4)
        self.assertTrue(any(row.is_abstention for row in selected))
        self.assertTrue(
            any(row.question_type.startswith("single-session") for row in selected)
        )
        self.assertTrue(any(row.question_type == "multi-session" for row in selected))
        self.assertTrue(
            any(
                row.question_type in {"temporal-reasoning", "knowledge-update"}
                for row in selected
            )
        )

    def test_provisional_evaluator_is_explicitly_limited(self):
        correct = MODULE.provisional_evaluate(
            "My favorite is blue", "blue", is_abstention=False
        )
        unknown = MODULE.provisional_evaluate(
            "The answer is unknown", "anything", is_abstention=True
        )
        self.assertEqual(correct["score"], 1)
        self.assertEqual(unknown["score"], 1)
        self.assertIn("Not the official", correct["limitation"])

    def test_bm25_scores_are_deterministic(self):
        sessions = (
            Session(
                "relevant",
                "2026-01-01",
                (Turn("user", "favorite color blue"),),
            ),
            Session(
                "other",
                "2026-01-02",
                (Turn("user", "ordered pizza"),),
            ),
        )
        first = MODULE.bm25_scores("favorite color", sessions, k=1)
        second = MODULE.bm25_scores("favorite color", sessions, k=1)
        self.assertEqual(first, second)
        self.assertEqual(first[0][0].session_id, "relevant")


if __name__ == "__main__":
    unittest.main()
