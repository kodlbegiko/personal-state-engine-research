from __future__ import annotations

import math
from collections import Counter
from typing import Any

from .zero_cost_baselines import _stem, cosine_overlap, parse_timestamp, recency, tokens

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "what", "when", "where", "which", "who", "whose", "how", "does", "do",
    "did", "to", "of", "in", "on", "at", "for", "from", "with", "and", "or",
    "under", "user", "users", "s", "this", "that", "it", "as", "still",
    "treated", "should", "current", "latest", "now",
}

STRONG_UPDATE_STEMS = {
    _stem(token)
    for token in {
        "updated", "replace", "replaced", "changed", "stopped", "correction",
        "corrected", "moved", "rescheduled", "revoked",
    }
}
WEAK_UPDATE_STEMS = {_stem(token) for token in {"new", "current", "now"}}
ADVERSARIAL_STEMS = {
    _stem(token)
    for token in {
        "ignore", "query", "question", "discuss", "discussed", "keyword",
        "keywords", "stuffing", "decoy", "unrelated", "fake", "fabricated",
        "wrong", "answer", "instruction", "prompt",
    }
}
QUESTION_WORDS = {"what", "when", "where", "which", "who", "how", "does", "do", "did"}

# Frozen in experiments/protocols/pse-candidate-v2-preregistration.json.
SIMILARITY_CAP = 0.72
BASE_SIMILARITY_WEIGHT = 0.45
BASE_CONSTANT = 0.20
RECENCY_WEIGHT = 0.10
STRONG_UPDATE_BONUS = 0.18
WEAK_UPDATE_BONUS = 0.05
RARE_ANCHOR_WEIGHT = 0.12
NOVEL_BONUS_PER_TOKEN = 0.02
NOVEL_BONUS_TOKEN_CAP = 3
ECHO_PENALTY = 0.28
ADVERSARIAL_CUE_PENALTY = 0.20
ECHO_ANCHOR_THRESHOLD = 0.75
ECHO_QUERY_ONLY_THRESHOLD = 0.80
ECHO_REPETITION_THRESHOLD = 0.15
ECHO_NOVEL_TOKEN_MAX = 1


def content_tokens(text: str) -> list[str]:
    values: list[str] = []
    for token in tokens(text):
        stem = _stem(token)
        if token in STOPWORDS or stem in STOPWORDS or len(stem) <= 1:
            continue
        values.append(stem)
    return values


def pse_candidate_v2_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    """Deterministic CPU-only PSE v2 retrieval candidate.

    The candidate is deliberately narrow: it preserves explicit state-transition
    evidence while resisting lexical-copy and keyword-stuffing distractors.
    It uses no embeddings, no case IDs, and no benchmark-specific answer strings.
    """
    q_content = set(content_tokens(case["query"]))
    n_docs = max(len(case["memories"]), 1)
    query_df: Counter[str] = Counter()
    for memory in case["memories"]:
        memory_terms = set(content_tokens(memory["text"]))
        for term in q_content & memory_terms:
            query_df[term] += 1

    query_idf = {
        term: math.log((1 + n_docs) / (1 + query_df.get(term, 0))) + 1.0
        for term in q_content
    }
    query_idf_total = sum(query_idf.values()) or 1.0
    scored: list[tuple[float, object, int, str]] = []

    for index, memory in enumerate(case["memories"]):
        text = memory["text"]
        raw_tokens = tokens(text)
        memory_stems = {_stem(token) for token in raw_tokens}
        memory_content = set(content_tokens(text))

        similarity = min(cosine_overlap(text, case["query"]), SIMILARITY_CAP)
        base = (
            BASE_SIMILARITY_WEIGHT * similarity
            + BASE_CONSTANT
            + RECENCY_WEIGHT * recency(memory)
        )

        if memory_stems & STRONG_UPDATE_STEMS:
            update_bonus = STRONG_UPDATE_BONUS
        elif memory_stems & WEAK_UPDATE_STEMS:
            update_bonus = WEAK_UPDATE_BONUS
        else:
            update_bonus = 0.0

        overlap = q_content & memory_content
        anchor_coverage = (
            sum(query_idf[token] for token in overlap) / query_idf_total
            if q_content
            else 0.0
        )
        novel = memory_content - q_content
        anchor_bonus = RARE_ANCHOR_WEIGHT * anchor_coverage
        novel_bonus = (
            min(len(novel), NOVEL_BONUS_TOKEN_CAP) * NOVEL_BONUS_PER_TOKEN
            if overlap
            else 0.0
        )

        content_raw = [
            _stem(token)
            for token in raw_tokens
            if token not in STOPWORDS and len(_stem(token)) > 1
        ]
        query_only_fraction = (
            sum(token in q_content for token in content_raw) / len(content_raw)
            if content_raw
            else 0.0
        )
        repetition = (
            1.0 - len(set(content_raw)) / len(content_raw)
            if content_raw
            else 0.0
        )
        begins_question = bool(raw_tokens and raw_tokens[0] in QUESTION_WORDS)
        echo_like = (
            anchor_coverage >= ECHO_ANCHOR_THRESHOLD
            and len(novel) <= ECHO_NOVEL_TOKEN_MAX
            and (
                text.strip().endswith("?")
                or begins_question
                or (
                    query_only_fraction >= ECHO_QUERY_ONLY_THRESHOLD
                    and repetition >= ECHO_REPETITION_THRESHOLD
                )
            )
        )
        echo_penalty = ECHO_PENALTY if echo_like else 0.0
        adversarial_penalty = (
            ADVERSARIAL_CUE_PENALTY if ADVERSARIAL_STEMS & memory_stems else 0.0
        )

        score = base + update_bonus + anchor_bonus + novel_bonus - echo_penalty - adversarial_penalty
        scored.append(
            (round(score, 6), parse_timestamp(memory.get("timestamp")), -index, memory["id"])
        )

    scored.sort(reverse=True)
    return [memory_id for _, _, _, memory_id in scored[:k]]
