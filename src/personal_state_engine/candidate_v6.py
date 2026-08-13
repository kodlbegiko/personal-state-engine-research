from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .candidate_v2 import pse_candidate_v2_rank
from .zero_cost_baselines import _stem, parse_timestamp, tokens

VERDICT_SUPPORTED = "SUPPORTED"
VERDICT_INSUFFICIENT = "INSUFFICIENT"
VERDICT_CONTRADICTED = "CONTRADICTED"
VERDICT_AMBIGUOUS = "AMBIGUOUS"

ASSERTED_VALUE = "ASSERTED_VALUE"
ASSERTED_RELATION = "ASSERTED_RELATION"
NEGATED_VALUE = "NEGATED_VALUE"
NO_VALUE_RECORDED = "NO_VALUE_RECORDED"
META_DISCUSSION = "META_DISCUSSION"
QUESTION = "QUESTION"
AGENDA_ITEM = "AGENDA_ITEM"
REVIEW_TOPIC = "REVIEW_TOPIC"
UNRESOLVED = "UNRESOLVED"
CONTRADICTION = "CONTRADICTION"
UNKNOWN = "UNKNOWN"

ROLE_ASSERTION = "ASSERTION"
ROLE_QUESTION = "QUESTION"
ROLE_AGENDA = "AGENDA"
ROLE_REVIEW = "REVIEW"
ROLE_META = "META"
ROLE_NO_VALUE = "NO_VALUE"
ROLE_UNRESOLVED = "UNRESOLVED"
ROLE_NEGATIVE = "NEGATIVE"
ROLE_UNKNOWN = "UNKNOWN"

RELATION_ALIASES: dict[str, tuple[str, ...]] = {
    "phone": ("phone number", "phone", "telephone", "mobile"),
    "email": ("email address", "email", "e-mail", "mailbox"),
    "budget": ("budget",),
    "balance": ("balance",),
    "price": ("price", "cost"),
    "salary": ("salary", "wage"),
    "address": ("mailing address", "address"),
    "location": ("location", "room", "site", "shelf", "cabinet"),
    "date": ("date", "day"),
    "time": ("time", "hour"),
    "color": ("color", "colour"),
    "status": ("status", "state"),
    "owner": ("owner", "responsible person", "ownership"),
    "code": ("code", "passcode"),
    "pin": ("pin", "password"),
    "serial_number": ("serial number", "serial"),
    "version": ("version",),
    "provider": ("provider", "vendor", "supplier"),
    "preference": ("preference", "preferred", "favorite", "favourite"),
    "approval": ("approval", "reviewer"),
    "timezone": ("timezone", "time zone"),
    "registration_number": ("registration number", "registration", "plate"),
    "expiry": ("expiry", "expiration", "deadline", "due date"),
    "quantity": ("quantity", "count"),
    "type": ("type", "kind", "category"),
}

ALIAS_TO_RELATION: dict[str, str] = {}
for _relation, _aliases in RELATION_ALIASES.items():
    for _alias in _aliases:
        ALIAS_TO_RELATION[_alias.casefold()] = _relation

RELATION_PATTERN = "|".join(
    re.escape(alias)
    for alias in sorted(ALIAS_TO_RELATION, key=lambda item: (-len(item), item))
)
SUBJECT_PATTERN = r"[A-Za-z][A-Za-z0-9_-]*"
VALUE_PATTERN = r"[^,;.!?]+?"

CURRENT_STEMS = {_stem(x) for x in {"current", "latest", "now", "currently"}}
STALE_STEMS = {
    _stem(x)
    for x in {"old", "previous", "prior", "stale", "historical", "formerly", "superseded", "obsolete", "archive", "before"}
}
RESOLUTION_STEMS = {
    _stem(x)
    for x in {"updated", "update", "replaced", "replace", "changed", "change", "corrected", "correction", "supersedes"}
}
INFERENCE_STEMS = {
    _stem(x)
    for x in {"probably", "likely", "guess", "assume", "assuming", "suggests", "implies", "maybe", "might", "possibly", "perhaps", "tentative"}
}
GENERIC_STEMS = {
    _stem(x)
    for x in {
        "what", "which", "who", "where", "when", "how", "is", "are", "was", "were", "does", "do", "did",
        "the", "a", "an", "of", "for", "to", "at", "on", "in", "and", "or", "with", "current", "latest", "now",
        "currently", "please", "tell", "me", "recorded", "known", "value", "values", "has", "have", "uses", "use",
        "used", "set", "confirmed", "final", "official", "this", "that", "fact", "note", "notes", "session", "meeting",
    }
}
ALL_RELATION_STEMS = {
    _stem(token)
    for aliases in RELATION_ALIASES.values()
    for alias in aliases
    for token in alias.split()
}

QUESTION_PATTERNS = (
    re.compile(r"^\s*(?:what|which|who|where|when|how|does|do|did|is|are)\b", re.I),
    re.compile(r"\bquestion\s+(?:about|regarding|for|repeated|restated)\b", re.I),
    re.compile(r"\b(?:repeat|repeated|restate|restated|paraphrase|paraphrased)\s+(?:the\s+)?question\b", re.I),
)
AGENDA_PATTERNS = (
    re.compile(r"\bagenda\b", re.I),
    re.compile(r"\b(?:agenda|action)\s+item\b", re.I),
)
REVIEW_PATTERNS = (
    re.compile(r"\breview\s+(?:of|about|regarding|topic)\b", re.I),
    re.compile(r"\btopic\s+(?:only|for|about|regarding)\b", re.I),
    re.compile(r"\b(?:discussion|discussion topic)\s+(?:of|about|regarding)\b", re.I),
)
NO_VALUE_PATTERNS = (
    re.compile(r"\bno\s+(?:recorded|known|confirmed|current|available|explicit|direct)?\s*(?:answer|value|result|record)\b", re.I),
    re.compile(r"\b(?:answer|value|result|record)\s+(?:is\s+)?(?:missing|absent|unknown|unavailable|not\s+present|not\s+recorded)\b", re.I),
    re.compile(r"\bcontains?\s+no\s+(?:recorded|known|confirmed|available)?\s*(?:answer|value|result)\b", re.I),
    re.compile(r"\bwithout\s+(?:a\s+)?(?:recorded|known|confirmed|available)?\s*(?:answer|value|result)\b", re.I),
    re.compile(r"\banswer\s+not\s+present\b", re.I),
)
UNRESOLVED_PATTERNS = (
    re.compile(r"\b(?:remains?|still)\s+(?:unresolved|unknown|pending|uncertain)\b", re.I),
    re.compile(r"\b(?:unresolved|pending|uncertain)\s+(?:question|issue|value|answer)\b", re.I),
)
META_PATTERNS = (
    re.compile(r"\b(?:discuss|discussed|discussion|mention|mentioned)\b", re.I),
    re.compile(r"\b(?:prompt|instruction|keyword|query)\b", re.I),
)
NEGATIVE_PATTERNS = (
    re.compile(r"\b(?:is|was|are|were)\s+not\b", re.I),
    re.compile(r"\bdo\s+not\s+use\b", re.I),
    re.compile(r"\b(?:wrong|incorrect|invalid)\s+(?:answer|value|code|number|email|phone|version|status|provider|owner)\b", re.I),
)

ASSERTION_PATTERNS = (
    re.compile(
        rf"(?:^|:\s*|;\s*)(?:the\s+)?(?:(?P<scope>current|latest|old|previous|prior|historical)\s+)?"
        rf"(?P<relation>{RELATION_PATTERN})\s+(?:for|of)\s+(?P<subject>{SUBJECT_PATTERN})\s+"
        rf"(?:is|was|=|:)\s*(?P<value>{VALUE_PATTERN})(?=$|[,;.!?])",
        re.I,
    ),
    re.compile(
        rf"(?:^|:\s*|;\s*)(?P<subject>{SUBJECT_PATTERN})(?:'s)?\s+"
        rf"(?:(?P<scope>current|latest|old|previous|prior|historical)\s+)?(?P<relation>{RELATION_PATTERN})\s+"
        rf"(?:is|was|=|:)\s*(?P<value>{VALUE_PATTERN})(?=$|[,;.!?])",
        re.I,
    ),
    re.compile(
        rf"(?:^|:\s*|;\s*)(?:the\s+)?(?:(?P<scope>current|latest)\s+)?(?P<relation>{RELATION_PATTERN})\s+"
        rf"(?:for|of)\s+(?P<subject>{SUBJECT_PATTERN})\s+(?:changed|updated|corrected|replaced)\s+(?:to|as)\s+"
        rf"(?P<value>{VALUE_PATTERN})(?=$|[,;.!?])",
        re.I,
    ),
    re.compile(
        rf"(?:^|:\s*|;\s*)(?P<subject>{SUBJECT_PATTERN})\s+(?P<relation>{RELATION_PATTERN})\s+"
        rf"(?:changed|updated|corrected|replaced)\s+(?:to|as)\s+(?P<value>{VALUE_PATTERN})(?=$|[,;.!?])",
        re.I,
    ),
)


@dataclass(frozen=True)
class EvidenceObject:
    source_memory_id: str
    subject: str | None
    predicate: str | None
    object_or_value: str | None
    assertion_type: str
    polarity: str
    temporal_scope: str
    discourse_role: str
    parse_status: str
    timestamp: object
    resolving: bool = False


def _stems(text: str) -> set[str]:
    return {_stem(token) for token in tokens(text)}


def relation_concepts(text: str) -> set[str]:
    lowered = text.casefold()
    result: set[str] = set()
    for alias, relation in ALIAS_TO_RELATION.items():
        if re.search(rf"(?<![A-Za-z0-9_-]){re.escape(alias)}(?![A-Za-z0-9_-])", lowered):
            result.add(relation)
    return result


def _canonical_relation(alias: str | None) -> str | None:
    if alias is None:
        return None
    return ALIAS_TO_RELATION.get(alias.casefold())


def _entity_anchors(query: str) -> set[str]:
    atoms = re.findall(SUBJECT_PATTERN, query)
    anchors: set[str] = set()
    for index, atom in enumerate(atoms):
        stem = _stem(atom)
        if stem in GENERIC_STEMS or stem in ALL_RELATION_STEMS or stem in CURRENT_STEMS:
            continue
        if any(char.isdigit() for char in atom) or "-" in atom or (atom[0].isupper() and index > 0):
            anchors.add(atom.casefold())
    return anchors


def _temporal_scope(text: str, explicit_scope: str | None = None) -> str:
    stems = _stems(text)
    if explicit_scope and _stem(explicit_scope) in STALE_STEMS:
        return "STALE"
    if explicit_scope and _stem(explicit_scope) in CURRENT_STEMS:
        return "CURRENT"
    if stems & STALE_STEMS:
        return "STALE"
    if stems & (CURRENT_STEMS | RESOLUTION_STEMS):
        return "CURRENT"
    return "UNSPECIFIED"


def _first_match(patterns: tuple[re.Pattern[str], ...], text: str) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def classify_discourse_role(text: str) -> tuple[str, str]:
    """Classify discourse before any value extraction.

    Ordering is selection-critical: explicit absence and non-assertion discourse
    cannot leak residual tokens into the value slot extractor.
    """
    if _first_match(NO_VALUE_PATTERNS, text):
        return ROLE_NO_VALUE, NO_VALUE_RECORDED
    if _first_match(AGENDA_PATTERNS, text):
        return ROLE_AGENDA, AGENDA_ITEM
    if _first_match(QUESTION_PATTERNS, text) or text.strip().endswith("?"):
        return ROLE_QUESTION, QUESTION
    if _first_match(REVIEW_PATTERNS, text):
        return ROLE_REVIEW, REVIEW_TOPIC
    if _first_match(UNRESOLVED_PATTERNS, text) or (_stems(text) & INFERENCE_STEMS):
        return ROLE_UNRESOLVED, UNRESOLVED
    if _first_match(NEGATIVE_PATTERNS, text):
        return ROLE_NEGATIVE, NEGATED_VALUE
    if _first_match(META_PATTERNS, text):
        return ROLE_META, META_DISCUSSION
    return ROLE_ASSERTION, UNKNOWN


def _normalize_value(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().strip("\"'()[]{}<> ")).casefold()


def _subject_matches_query(subject: str | None, query: str) -> bool:
    anchors = _entity_anchors(query)
    if not anchors:
        return True
    return subject is not None and subject.casefold() in anchors


def _nonassertion_object(memory: dict[str, Any], query: str, role: str, assertion_type: str) -> EvidenceObject:
    relations = sorted(relation_concepts(memory["text"]) & relation_concepts(query))
    predicate = relations[0] if len(relations) == 1 else None
    anchors = _entity_anchors(query)
    subject = next((anchor for anchor in sorted(anchors) if anchor in memory["text"].casefold()), None)
    return EvidenceObject(
        source_memory_id=memory["id"],
        subject=subject,
        predicate=predicate,
        object_or_value=None,
        assertion_type=assertion_type,
        polarity="NEGATIVE" if assertion_type == NEGATED_VALUE else "NONE",
        temporal_scope=_temporal_scope(memory["text"]),
        discourse_role=role,
        parse_status="NON_ASSERTION",
        timestamp=parse_timestamp(memory.get("timestamp")),
        resolving=False,
    )


def parse_evidence_object(memory: dict[str, Any], query: str) -> EvidenceObject:
    text = memory["text"]
    role, classified_type = classify_discourse_role(text)
    if role != ROLE_ASSERTION:
        return _nonassertion_object(memory, query, role, classified_type)

    query_relations = relation_concepts(query)
    for pattern in ASSERTION_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        predicate = _canonical_relation(match.group("relation"))
        subject = match.group("subject")
        value = _normalize_value(match.group("value"))
        if not value:
            continue
        if query_relations and predicate not in query_relations:
            continue
        if not _subject_matches_query(subject, query):
            continue
        resolving = bool(_stems(text) & RESOLUTION_STEMS)
        return EvidenceObject(
            source_memory_id=memory["id"],
            subject=subject.casefold(),
            predicate=predicate,
            object_or_value=value,
            assertion_type=ASSERTED_VALUE,
            polarity="POSITIVE",
            temporal_scope=_temporal_scope(text, match.groupdict().get("scope")),
            discourse_role=ROLE_ASSERTION,
            parse_status="PARSED",
            timestamp=parse_timestamp(memory.get("timestamp")),
            resolving=resolving,
        )

    return EvidenceObject(
        source_memory_id=memory["id"],
        subject=None,
        predicate=None,
        object_or_value=None,
        assertion_type=UNKNOWN,
        polarity="NONE",
        temporal_scope=_temporal_scope(text),
        discourse_role=ROLE_UNKNOWN,
        parse_status="FAIL_CLOSED",
        timestamp=parse_timestamp(memory.get("timestamp")),
        resolving=False,
    )


def _required_relations(query: str) -> list[str]:
    relations = sorted(relation_concepts(query))
    return relations or ["generic"]


def _is_current_query(query: str) -> bool:
    return bool(_stems(query) & CURRENT_STEMS)


def answerability_signature(case: dict[str, Any], ranking: list[str] | None = None) -> dict[str, Any]:
    ranking = ranking if ranking is not None else pse_candidate_v2_rank(case, 5)
    by_id = {memory["id"]: memory for memory in case["memories"]}
    requirements = _required_relations(case["query"])
    parsed: list[EvidenceObject] = []
    coverage: dict[str, list[EvidenceObject]] = {requirement: [] for requirement in requirements}

    for memory_id in ranking:
        memory = by_id.get(memory_id)
        if memory is None:
            continue
        evidence = parse_evidence_object(memory, case["query"])
        parsed.append(evidence)
        if evidence.assertion_type != ASSERTED_VALUE or evidence.object_or_value is None:
            continue
        if evidence.polarity != "POSITIVE":
            continue
        if _is_current_query(case["query"]) and evidence.temporal_scope == "STALE":
            continue
        for requirement in requirements:
            if requirement == "generic" or evidence.predicate == requirement:
                coverage[requirement].append(evidence)

    missing = [requirement for requirement, values in coverage.items() if not values]
    if missing:
        return {
            "verdict": VERDICT_INSUFFICIENT,
            "requirements": requirements,
            "missing_requirements": missing,
            "coverage": {key: [item.source_memory_id for item in value] for key, value in coverage.items()},
            "parsed_objects": parsed,
        }

    selected: dict[str, list[EvidenceObject]] = {}
    for requirement, values in coverage.items():
        resolving = [item for item in values if item.resolving]
        if resolving:
            latest_time = max(item.timestamp for item in resolving)
            latest = [item for item in resolving if item.timestamp == latest_time]
            latest_values = {item.object_or_value for item in latest}
            if len(latest_values) != 1:
                return {
                    "verdict": VERDICT_AMBIGUOUS,
                    "requirements": requirements,
                    "missing_requirements": [],
                    "coverage": {key: [item.source_memory_id for item in value] for key, value in coverage.items()},
                    "ambiguous_requirement": requirement,
                    "parsed_objects": parsed,
                }
            selected[requirement] = latest
            continue

        current_values = [item for item in values if item.temporal_scope != "STALE"]
        distinct = {item.object_or_value for item in current_values}
        if len(distinct) > 1:
            return {
                "verdict": VERDICT_CONTRADICTED,
                "requirements": requirements,
                "missing_requirements": [],
                "coverage": {key: [item.source_memory_id for item in value] for key, value in coverage.items()},
                "contradicted_requirement": requirement,
                "parsed_objects": parsed,
            }
        selected[requirement] = current_values or values

    return {
        "verdict": VERDICT_SUPPORTED,
        "requirements": requirements,
        "missing_requirements": [],
        "coverage": {key: [item.source_memory_id for item in value] for key, value in selected.items()},
        "parsed_objects": parsed,
    }


def pse_candidate_v6_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    """Candidate-v6: frozen Candidate-v2 ranking gated by typed assertions."""
    ranking = pse_candidate_v2_rank(case, k)
    signature = answerability_signature(case, ranking)
    return ranking if signature["verdict"] == VERDICT_SUPPORTED else []
