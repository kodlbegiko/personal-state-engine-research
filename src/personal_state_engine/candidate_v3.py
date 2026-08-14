from __future__ import annotations

from typing import Any

from .candidate_v2 import pse_candidate_v2_rank
from .zero_cost_baselines import _stem, tokens

# Candidate-v3 is a new candidate identity. It deliberately does not modify
# candidate-v2 ranking semantics; it adds a separate, deterministic evidence-
# sufficiency representation and filters the frozen v2 ranking through it.

# Relation concepts are intentionally field-granular where confusing adjacent
# attributes would create false evidence (for example email vs phone, budget vs
# balance, PIN vs generic number). They are generic concepts rather than case IDs
# or answer strings.
RELATION_CONCEPTS: dict[str, set[str]] = {
    "number": {"number", "no", "serial", "號碼", "編號"},
    "code": {"code", "passcode", "代碼"},
    "pin": {"pin", "password", "密碼"},
    "ownership": {"owner", "own", "owns", "owned", "responsible", "負責", "負責人"},
    "floor": {"floor", "level", "樓層"},
    "address": {"address", "地址"},
    "location": {"location", "site", "room", "地點", "位置"},
    "date": {"date", "day", "日期", "哪天"},
    "expiry": {"expire", "expiry", "expires", "expired", "end", "ends", "deadline", "due", "到期", "截止"},
    "preference": {"prefer", "preferred", "prefers", "preference", "favorite", "favourite", "likes", "喜歡", "偏好"},
    "balance": {"balance", "餘額"},
    "budget": {"budget", "預算"},
    "price": {"price", "cost", "價格", "費用"},
    "salary": {"salary", "wage", "薪資", "薪水"},
    "amount": {"amount", "total", "金額", "總額"},
    "type": {"type", "kind", "category", "class", "類型", "種類"},
    "hint": {"hint", "clue", "提示", "線索"},
    "shop": {"shop", "store", "cafe", "coffee", "restaurant", "咖啡店", "商店", "餐廳"},
    "status": {"status", "state", "condition", "狀態", "情況"},
    "phone": {"phone", "telephone", "mobile", "電話", "手機"},
    "email": {"email", "e-mail", "mailbox", "信箱", "電子郵件"},
    "color": {"color", "colour", "顏色"},
    "quantity": {"count", "quantity", "many", "數量"},
    "registration": {"registration", "plate", "登記", "車牌"},
}

UNCERTAIN_MARKERS = {
    "might", "maybe", "possibly", "possible", "tentative", "tentatively",
    "could", "may", "perhaps", "estimate", "estimated", "可能", "也許", "暫定", "大概",
}
CERTAINTY_QUERY_MARKERS = {
    "confirmed", "confirm", "final", "definite", "official", "確定", "確認", "最終", "正式",
}
DISCOURSE_MARKERS = {
    "answer", "query", "question", "keyword", "keywords", "prompt", "instruction",
    "stuffing", "decoy", "fake", "fabricated", "回答", "問題", "關鍵字", "提示詞",
}
GENERIC_FUNCTION_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "what", "when", "where", "which", "who", "whose", "how", "does", "do", "did",
    "to", "of", "in", "on", "at", "for", "from", "with", "and", "or", "under",
    "this", "that", "it", "as", "now", "current", "latest", "still", "user", "users",
}
CJK_FUNCTION_BIGRAMS = {"的是", "是在", "哪一", "一間", "多少", "目前", "現在", "請問"}


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _cjk_bigrams(text: str) -> set[str]:
    chars = [char for char in text if "\u4e00" <= char <= "\u9fff"]
    return {"".join(chars[index:index + 2]) for index in range(len(chars) - 1)}


def _alias_present(text: str, alias: str) -> bool:
    if _contains_cjk(alias):
        return alias in text
    stems = {_stem(token) for token in tokens(text)}
    return _stem(alias) in stems


def relation_concepts(text: str) -> set[str]:
    concepts: set[str] = set()
    for concept, aliases in RELATION_CONCEPTS.items():
        if any(_alias_present(text, alias) for alias in aliases):
            concepts.add(concept)
    return concepts


def query_requires_certainty(query: str) -> bool:
    lowered = query.casefold()
    return any(marker in lowered for marker in CERTAINTY_QUERY_MARKERS)


def memory_is_uncertain(text: str) -> bool:
    lowered = text.casefold()
    english_tokens = set(lowered.split())
    for marker in UNCERTAIN_MARKERS:
        if _contains_cjk(marker):
            if marker in text:
                return True
        elif marker in english_tokens:
            return True
    return False


def question_echo(memory_text: str, query: str) -> bool:
    normalized_memory = memory_text.strip().casefold().rstrip("?？")
    normalized_query = query.strip().casefold().rstrip("?？")
    return normalized_memory == normalized_query


def _relation_alias_stems() -> set[str]:
    output: set[str] = set()
    for aliases in RELATION_CONCEPTS.values():
        for alias in aliases:
            if not _contains_cjk(alias):
                output.add(_stem(alias))
    return output


RELATION_ALIAS_STEMS = _relation_alias_stems()
DISCOURSE_STEMS = {_stem(marker) for marker in DISCOURSE_MARKERS if not _contains_cjk(marker)}
GENERIC_STEMS = {_stem(marker) for marker in GENERIC_FUNCTION_WORDS}
UNCERTAIN_STEMS = {_stem(marker) for marker in UNCERTAIN_MARKERS if not _contains_cjk(marker)}


def has_asserted_value(memory_text: str, query: str) -> bool:
    """Return True when evidence contains content beyond query/relation boilerplate."""
    if _contains_cjk(memory_text) or _contains_cjk(query):
        memory_extra = _cjk_bigrams(memory_text) - _cjk_bigrams(query)
        relation_bigrams: set[str] = set()
        for aliases in RELATION_CONCEPTS.values():
            for alias in aliases:
                if _contains_cjk(alias):
                    relation_bigrams |= _cjk_bigrams(alias)
        meaningful = {
            bigram for bigram in memory_extra
            if bigram not in relation_bigrams and bigram not in CJK_FUNCTION_BIGRAMS
        }
        return bool(meaningful)

    query_stems = {_stem(token) for token in tokens(query)}
    for token in tokens(memory_text):
        stem = _stem(token)
        if stem in query_stems:
            continue
        if stem in GENERIC_STEMS or stem in DISCOURSE_STEMS or stem in UNCERTAIN_STEMS:
            continue
        if stem in RELATION_ALIAS_STEMS:
            continue
        return True
    return False


def evidence_supports_query(memory_text: str, query: str) -> bool:
    requested = relation_concepts(query)
    supported = relation_concepts(memory_text)
    if requested and not requested.issubset(supported):
        return False
    if query_requires_certainty(query) and memory_is_uncertain(memory_text):
        return False
    if question_echo(memory_text, query):
        return False
    if not has_asserted_value(memory_text, query):
        return False
    return True


def evidence_sufficiency_signature(case: dict[str, Any], ranking: list[str]) -> dict[str, Any]:
    by_id = {memory["id"]: memory for memory in case["memories"]}
    supported_ids = [
        memory_id
        for memory_id in ranking
        if memory_id in by_id and evidence_supports_query(by_id[memory_id]["text"], case["query"])
    ]
    return {
        "requested_concepts": sorted(relation_concepts(case["query"])),
        "query_requires_certainty": query_requires_certainty(case["query"]),
        "supported_memory_ids": supported_ids,
        "sufficient": bool(supported_ids),
    }


def pse_candidate_v3_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    """Candidate-v3: frozen v2 ordering filtered by evidence sufficiency."""
    ranking = pse_candidate_v2_rank(case, k)
    signature = evidence_sufficiency_signature(case, ranking)
    return signature["supported_memory_ids"][:k]
