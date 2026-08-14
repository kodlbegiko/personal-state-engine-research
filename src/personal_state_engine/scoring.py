from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class ScoreDecision:
    passed: bool
    score: float
    reasons: tuple[str, ...]
    evaluator_version: str = "structured-exact-v1"


@dataclass(frozen=True, slots=True)
class BinarySummary:
    n: int
    successes: int
    rate: float
    lower_95: float
    upper_95: float


@dataclass(frozen=True, slots=True)
class PairedComparison:
    pairs: int
    left_only: int
    right_only: int
    difference: float
    exact_p_value: float


class StructuredOutcomeScorer:
    """Independent deterministic scorer for structured outcome fields."""

    version = "structured-exact-v1"

    def score(self, expected: dict[str, Any], observed: dict[str, Any]) -> ScoreDecision:
        mismatches: list[str] = []
        self._compare(expected, observed, path="$", mismatches=mismatches)
        return ScoreDecision(not mismatches, 1.0 if not mismatches else 0.0, tuple(mismatches))

    def _compare(self, expected: Any, observed: Any, *, path: str, mismatches: list[str]) -> None:
        if isinstance(expected, dict):
            if not isinstance(observed, dict):
                mismatches.append(f"{path}:expected_object")
                return
            for key, value in expected.items():
                if key not in observed:
                    mismatches.append(f"{path}.{key}:missing")
                else:
                    self._compare(value, observed[key], path=f"{path}.{key}", mismatches=mismatches)
            return
        if isinstance(expected, list):
            if not isinstance(observed, list) or expected != observed:
                mismatches.append(f"{path}:list_mismatch")
            return
        if expected != observed:
            mismatches.append(f"{path}:expected={expected!r}:observed={observed!r}")


def wilson_interval(successes: int, n: int, *, z: float = 1.959963984540054) -> BinarySummary:
    if n <= 0 or not 0 <= successes <= n:
        raise ValueError("require 0 <= successes <= n and n > 0")
    rate = successes / n
    denominator = 1 + z * z / n
    centre = (rate + z * z / (2 * n)) / denominator
    margin = z * math.sqrt(rate * (1 - rate) / n + z * z / (4 * n * n)) / denominator
    return BinarySummary(n, successes, rate, max(0.0, centre - margin), min(1.0, centre + margin))


def summarise_binary(values: Iterable[bool]) -> BinarySummary:
    materialized = list(values)
    return wilson_interval(sum(materialized), len(materialized))


def paired_mcnemar(left: dict[str, bool], right: dict[str, bool]) -> PairedComparison:
    if set(left) != set(right) or not left:
        raise ValueError("paired comparisons require the same non-empty keys")
    left_only = sum(left[key] and not right[key] for key in left)
    right_only = sum(right[key] and not left[key] for key in left)
    discordant = left_only + right_only
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(math.comb(discordant, k) for k in range(0, min(left_only, right_only) + 1))
        p_value = min(1.0, 2 * tail / (2**discordant))
    difference = (sum(right.values()) - sum(left.values())) / len(left)
    return PairedComparison(len(left), left_only, right_only, difference, p_value)
