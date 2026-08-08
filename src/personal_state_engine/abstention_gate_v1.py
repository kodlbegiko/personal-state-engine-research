from __future__ import annotations

from typing import Any

from .candidate_v2 import pse_candidate_v2_rank
from .zero_cost_baselines import cosine_overlap

SIMILARITY_THRESHOLD = 0.22


def _cjk_bigrams(text: str) -> set[str]:
    chars = [char for char in text if "\u4e00" <= char <= "\u9fff"]
    return {"".join(chars[index:index + 2]) for index in range(len(chars) - 1)}


def _cjk_similarity(left: str, right: str) -> float:
    a, b = _cjk_bigrams(left), _cjk_bigrams(right)
    return len(a & b) / len(a | b) if a and b else 0.0


def evidence_similarity(memory_text: str, query: str) -> float:
    return max(cosine_overlap(memory_text, query), _cjk_similarity(memory_text, query))


def _question_echo(memory_text: str, query: str) -> bool:
    normalized_memory = memory_text.strip().casefold()
    normalized_query = query.strip().casefold()
    if normalized_memory == normalized_query:
        return True
    return memory_text.rstrip().endswith("?") and evidence_similarity(memory_text, query) > 0.60


def abstention_gate_v1_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    """Conservative wrapper around frozen PSE candidate v2.

    Development selection required answerable recall >= 0.90 before maximizing
    no-evidence abstention accuracy. The frozen threshold retained 100% answerable
    development recall. This is auxiliary research, not part of candidate v2.
    """
    ranking = pse_candidate_v2_rank(case, k)
    if not ranking:
        return []
    by_id = {memory["id"]: memory for memory in case["memories"]}
    top_memory = by_id[ranking[0]]
    max_similarity = max(
        (evidence_similarity(memory["text"], case["query"]) for memory in case["memories"]),
        default=0.0,
    )
    if max_similarity < SIMILARITY_THRESHOLD:
        return []
    if _question_echo(top_memory["text"], case["query"]):
        return []
    return ranking
