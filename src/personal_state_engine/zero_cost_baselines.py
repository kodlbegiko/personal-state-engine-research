from __future__ import annotations

import hashlib
import math
import random
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Callable

TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
REFERENCE_TIME = datetime(2026, 8, 8, tzinfo=timezone.utc)
UPDATE_CUES = {"new", "updated", "replace", "changed", "change", "stopped", "current", "correction", "corrected", "wrong", "moved", "rescheduled", "revoked", "now"}
CURRENT_QUERY_CUES = {"current", "now", "correct", "latest", "still", "applies", "should"}


def tokens(text: str) -> list[str]:
    return [token.casefold() for token in TOKEN_RE.findall(text)]


def _stem(token: str) -> str:
    token = token.casefold()
    if len(token) > 4 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 3 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


UPDATE_STEMS = {_stem(token) for token in UPDATE_CUES}
CURRENT_QUERY_STEMS = {_stem(token) for token in CURRENT_QUERY_CUES}


def cosine_overlap(left: str, right: str) -> float:
    a, b = Counter(tokens(left)), Counter(tokens(right))
    if not a or not b:
        return 0.0
    numerator = sum(a[key] * b.get(key, 0) for key in a)
    denominator = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return numerator / denominator if denominator else 0.0


def jaccard_overlap(left: str, right: str) -> float:
    a, b = set(tokens(left)), set(tokens(right))
    return len(a & b) / len(a | b) if a or b else 0.0


def parse_timestamp(value: str | None) -> datetime:
    if not value:
        return REFERENCE_TIME
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return REFERENCE_TIME
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def recency(memory: dict[str, Any]) -> float:
    age_days = max(0.0, (REFERENCE_TIME - parse_timestamp(memory.get("timestamp"))).total_seconds() / 86400)
    return 1.0 / (1.0 + age_days / 30.0)


def random_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    ids = [memory["id"] for memory in case["memories"]]
    seed = int(hashlib.sha256(case["id"].encode("utf-8")).hexdigest()[:8], 16)
    random.Random(seed).shuffle(ids)
    return ids[:k]


def recency_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    ranked = sorted(enumerate(case["memories"]), key=lambda item: (parse_timestamp(item[1].get("timestamp")), -item[0]), reverse=True)
    return [memory["id"] for _, memory in ranked[:k]]


def lexical_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    ranked = sorted(((jaccard_overlap(memory["text"], case["query"]), -index, memory["id"]) for index, memory in enumerate(case["memories"])), reverse=True)
    return [memory_id for score, _, memory_id in ranked if score > 0][:k]


def _counter_cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    numerator = sum(left[key] * right.get(key, 0.0) for key in left)
    denominator = math.sqrt(sum(v * v for v in left.values())) * math.sqrt(sum(v * v for v in right.values()))
    return numerator / denominator if denominator else 0.0


def tfidf_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    docs = [tokens(memory["text"]) for memory in case["memories"]]
    if not docs:
        return []
    query = Counter(tokens(case["query"]))
    df: Counter[str] = Counter()
    for doc in docs:
        for token in set(doc):
            df[token] += 1
    idf = {token: math.log((1 + len(docs)) / (1 + count)) + 1.0 for token, count in df.items()}
    doc_vectors = [Counter({token: count * idf.get(token, math.log(1 + len(docs)) + 1.0) for token, count in Counter(doc).items()}) for doc in docs]
    query_vector = Counter({token: count * idf.get(token, math.log(1 + len(docs)) + 1.0) for token, count in query.items()})
    scores = [_counter_cosine(doc, query_vector) for doc in doc_vectors]
    order = sorted(range(len(scores)), key=lambda i: (scores[i], -i), reverse=True)
    return [case["memories"][i]["id"] for i in order if scores[i] > 0][:k]


def bm25_rank(case: dict[str, Any], k: int = 5, k1: float = 1.5, b: float = 0.75) -> list[str]:
    docs = [tokens(memory["text"]) for memory in case["memories"]]
    if not docs:
        return []
    query = tokens(case["query"])
    avgdl = sum(len(doc) for doc in docs) / len(docs) or 1.0
    df: Counter[str] = Counter()
    for doc in docs:
        for token in set(doc):
            df[token] += 1
    scores: list[float] = []
    for doc in docs:
        tf = Counter(doc)
        score = 0.0
        for token in query:
            n = df.get(token, 0)
            if n == 0:
                continue
            idf = math.log(1.0 + (len(docs) - n + 0.5) / (n + 0.5))
            freq = tf.get(token, 0)
            denominator = freq + k1 * (1 - b + b * len(doc) / avgdl)
            if denominator:
                score += idf * (freq * (k1 + 1) / denominator)
        scores.append(score)
    order = sorted(range(len(scores)), key=lambda i: (scores[i], -i), reverse=True)
    return [case["memories"][i]["id"] for i in order if scores[i] > 0][:k]


def hybrid_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    scored = []
    for index, memory in enumerate(case["memories"]):
        lexical = jaccard_overlap(memory["text"], case["query"])
        score = 0.75 * lexical + 0.25 * recency(memory)
        scored.append((score, lexical, parse_timestamp(memory.get("timestamp")), -index, memory["id"]))
    scored.sort(reverse=True)
    return [memory_id for _, lexical, _, _, memory_id in scored if lexical > 0][:k]


def pse_current_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    """Mechanical reconstruction of retrieval.py blob 4339469... for benchmark-only records."""
    scored = []
    for index, memory in enumerate(case["memories"]):
        similarity = cosine_overlap(memory["text"], case["query"])
        score = 0.45 * similarity + 0.20 + 0.10 * recency(memory)
        scored.append((round(score, 6), parse_timestamp(memory.get("timestamp")), -index, memory["id"]))
    scored.sort(reverse=True)
    return [memory_id for _, _, _, memory_id in scored[:k]]


def pse_candidate_v1_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    """Current PSE score plus explicit state-transition evidence; frozen before hidden evaluation."""
    query_stems = {_stem(token) for token in tokens(case["query"])}
    current_query = bool(query_stems & CURRENT_QUERY_STEMS)
    scored = []
    for index, memory in enumerate(case["memories"]):
        similarity = cosine_overlap(memory["text"], case["query"])
        base = 0.45 * similarity + 0.20 + 0.10 * recency(memory)
        memory_stems = {_stem(token) for token in tokens(memory["text"])}
        update_bonus = 0.18 if memory_stems & UPDATE_STEMS else 0.0
        current_recency = 0.04 * recency(memory) if current_query else 0.0
        score = base + update_bonus + current_recency
        scored.append((round(score, 6), parse_timestamp(memory.get("timestamp")), -index, memory["id"]))
    scored.sort(reverse=True)
    return [memory_id for _, _, _, memory_id in scored[:k]]


RANKERS: dict[str, Callable[[dict[str, Any], int], list[str]]] = {
    "random": random_rank,
    "recency": recency_rank,
    "lexical": lexical_rank,
    "tfidf_local": tfidf_rank,
    "bm25_local": bm25_rank,
    "hybrid": hybrid_rank,
    "pse_current_reconstruction": pse_current_rank,
    "pse_candidate_v1": pse_candidate_v1_rank,
}


def evaluate_cases(cases: list[dict[str, Any]], ranker: Callable[[dict[str, Any], int], list[str]], k: int = 5) -> dict[str, Any]:
    answerable = [case for case in cases if case["relevant_memory_ids"]]
    abstention = [case for case in cases if not case["relevant_memory_ids"]]
    rows: list[dict[str, Any]] = []
    irrelevant = retrieved = 0
    for case in cases:
        ranking = ranker(case, k)
        relevant = set(case["relevant_memory_ids"])
        irrelevant += sum(memory_id not in relevant for memory_id in ranking)
        retrieved += len(ranking)
        if not relevant:
            continue
        row: dict[str, Any] = {"id": case["id"], "category": case["category"], "ranking": ranking}
        row["rr"] = next((1.0 / (index + 1) for index, memory_id in enumerate(ranking) if memory_id in relevant), 0.0)
        for depth in (1, 3, 5):
            top = set(ranking[:depth])
            row[f"recall@{depth}"] = len(relevant & top) / len(relevant)
            row[f"precision@{depth}"] = len(relevant & top) / depth
        dcg = sum((1.0 if memory_id in relevant else 0.0) / math.log2(index + 2) for index, memory_id in enumerate(ranking[:5]))
        ideal = sum(1.0 / math.log2(index + 2) for index in range(min(len(relevant), 5)))
        row["ndcg@5"] = dcg / ideal if ideal else 0.0
        rows.append(row)
    metrics: dict[str, float | None] = {}
    for key in ("recall@1", "recall@3", "recall@5", "precision@1", "precision@3", "precision@5", "rr", "ndcg@5"):
        metrics["MRR" if key == "rr" else key] = sum(row[key] for row in rows) / len(rows) if rows else None
    metrics["irrelevant_retrieval_rate"] = irrelevant / retrieved if retrieved else 0.0
    metrics["abstention_accuracy"] = sum(ranker(case, k) == [] for case in abstention) / len(abstention) if abstention else None
    return {"case_count": len(cases), "answerable_case_count": len(answerable), "abstention_case_count": len(abstention), "metrics": metrics, "per_case": rows}


def bootstrap_mrr_delta(cases: list[dict[str, Any]], left: Callable[[dict[str, Any], int], list[str]], right: Callable[[dict[str, Any], int], list[str]], iterations: int = 5000, seed: int = 20260808) -> dict[str, Any]:
    answerable = [case for case in cases if case["relevant_memory_ids"]]
    if len(answerable) < 2:
        return {"status": "UNDERPOWERED", "iterations": 0, "delta": None, "ci95": None}
    def rr(case: dict[str, Any], ranker: Callable[[dict[str, Any], int], list[str]]) -> float:
        relevant = set(case["relevant_memory_ids"])
        return next((1.0 / (i + 1) for i, mid in enumerate(ranker(case, 5)) if mid in relevant), 0.0)
    deltas = [rr(case, right) - rr(case, left) for case in answerable]
    rng = random.Random(seed)
    samples = []
    for _ in range(iterations):
        draw = [deltas[rng.randrange(len(deltas))] for _ in deltas]
        samples.append(sum(draw) / len(draw))
    samples.sort()
    lo = samples[int(0.025 * (len(samples) - 1))]
    hi = samples[int(0.975 * (len(samples) - 1))]
    return {"status": "UNDERPOWERED" if len(answerable) < 30 else "ESTIMATED", "iterations": iterations, "answerable_cases": len(answerable), "delta": sum(deltas) / len(deltas), "ci95": [lo, hi]}
