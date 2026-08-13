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

RAW_ATOM_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
VALUE_ATOM_RE = re.compile(r"[A-Za-z0-9@#._:/+-]+")

RELATION_ALIASES: dict[str, set[str]] = {
    "phone": {"phone", "telephone", "mobile"},
    "email": {"email", "mailbox", "e-mail"},
    "budget": {"budget"},
    "balance": {"balance"},
    "price": {"price", "cost"},
    "salary": {"salary", "wage"},
    "address": {"address", "mailing"},
    "location": {"location", "room", "site", "shelf", "cabinet"},
    "date": {"date", "day", "scheduled"},
    "time": {"time", "hour"},
    "color": {"color", "colour"},
    "status": {"status", "state"},
    "owner": {"owner", "responsible", "ownership"},
    "code": {"code", "passcode"},
    "pin": {"pin", "password"},
    "serial_number": {"serial", "serialnumber"},
    "version": {"version"},
    "provider": {"provider", "vendor", "supplier"},
    "preference": {"preference", "prefer", "preferred", "favorite", "favourite"},
    "approval": {"approval", "approved", "reviewer"},
    "timezone": {"timezone"},
    "registration_number": {"registration", "plate"},
    "expiry": {"expiry", "expires", "deadline", "due"},
    "quantity": {"quantity", "count"},
    "type": {"type", "kind", "category"},
}

RELATION_STEMS = {name: {_stem(alias) for alias in aliases} for name, aliases in RELATION_ALIASES.items()}
ALL_RELATION_STEMS = set().union(*RELATION_STEMS.values())

GENERIC_STEMS = {
    _stem(x)
    for x in {
        "what", "which", "who", "where", "when", "how", "is", "are", "was", "were",
        "does", "do", "did", "the", "a", "an", "of", "for", "to", "at", "on", "in",
        "and", "or", "with", "current", "latest", "now", "currently", "please", "tell",
        "me", "recorded", "known", "value", "values", "has", "have", "uses", "use",
        "used", "set", "confirmed", "final", "official", "belongs", "this", "fact",
        "note", "notes", "session", "meeting", "unrelated", "then",
    }
}
QUERY_TIME_STEMS = {_stem(x) for x in {"current", "latest", "now", "currently"}}
STALE_STEMS = {
    _stem(x) for x in {
        "old", "previous", "prior", "stale", "formerly", "superseded", "obsolete",
        "historical", "archive", "previously", "before",
    }
}
RESOLUTION_STEMS = {
    _stem(x) for x in {
        "updated", "update", "replaced", "replace", "changed", "change", "corrected",
        "correction", "supersedes",
    }
}
UNSUPPORTED_INFERENCE_STEMS = {
    _stem(x) for x in {
        "probably", "likely", "guess", "assume", "assuming", "suggests", "implies",
        "maybe", "might", "possibly", "plausibly",
    }
}
NO_EVIDENCE_STEMS = {
    _stem(x) for x in {
        "wrong", "incorrect", "invalid", "unknown", "unresolved", "unavailable",
        "missing", "absent", "without",
    }
}
NON_VALUE_STEMS = GENERIC_STEMS | QUERY_TIME_STEMS | STALE_STEMS | RESOLUTION_STEMS | UNSUPPORTED_INFERENCE_STEMS | NO_EVIDENCE_STEMS | ALL_RELATION_STEMS | {
    _stem(x) for x in {
        "query", "question", "answer", "discussion", "discussed", "topic", "only",
        "without", "period", "historical", "archive", "previously", "prior", "before",
        "repeat", "repeated", "restate", "restated", "paraphrase", "paraphrased",
    }
}


@dataclass(frozen=True)
class EvidenceProposition:
    memory_id: str
    relations: frozenset[str]
    values: frozenset[str]
    timestamp: object
    stale: bool
    resolving: bool


def relation_concepts(text: str) -> set[str]:
    stems = {_stem(token) for token in tokens(text)}
    return {name for name, aliases in RELATION_STEMS.items() if stems & aliases}


def _entity_anchors(query: str) -> set[str]:
    atoms = RAW_ATOM_RE.findall(query)
    anchors: set[str] = set()
    for index, atom in enumerate(atoms):
        stem = _stem(atom)
        if stem in GENERIC_STEMS or stem in ALL_RELATION_STEMS or stem in QUERY_TIME_STEMS:
            continue
        if any(char.isdigit() for char in atom) or "-" in atom or (atom[0].isupper() and index > 0):
            anchors.add(atom.casefold())
    return anchors


def _normalize_value_atom(raw: str) -> str:
    return raw.casefold().strip(".,:;!?()[]{}<>\"'")


def _query_raw_atoms(query: str) -> set[str]:
    return {normalized for raw in VALUE_ATOM_RE.findall(query) if (normalized := _normalize_value_atom(raw))}


def _asserted_value_tokens(memory_text: str, query: str) -> set[str]:
    query_stems = {_stem(token) for token in tokens(query)}
    query_raw = _query_raw_atoms(query)
    ignored = query_stems | NON_VALUE_STEMS
    values: set[str] = set()
    for raw in VALUE_ATOM_RE.findall(memory_text):
        normalized = _normalize_value_atom(raw)
        if not normalized or normalized in query_raw:
            continue
        stem = _stem(normalized)
        if stem in ignored or len(stem) <= 1:
            continue
        values.add(normalized)
    return values


def _near_echo_without_value(memory_text: str, query: str) -> bool:
    memory_stems = {_stem(token) for token in tokens(memory_text)}
    query_stems = {_stem(token) for token in tokens(query)}
    union = memory_stems | query_stems
    overlap = (len(memory_stems & query_stems) / len(union)) if union else 0.0
    if memory_text.strip().endswith("?") or overlap >= 0.80:
        return not _asserted_value_tokens(memory_text, query)
    return False


def _negative_or_inferential(text: str) -> bool:
    stems = {_stem(token) for token in tokens(text)}
    if stems & (NO_EVIDENCE_STEMS | UNSUPPORTED_INFERENCE_STEMS):
        return True
    lowered = text.casefold()
    if re.search(r"\bno\s+(?:confirmed|direct|recorded|known)?\s*", lowered):
        return True
    if "do not use" in lowered or "answer not present" in lowered:
        return True
    return False


def _parse_proposition(memory: dict[str, Any], query: str) -> EvidenceProposition | None:
    text = memory["text"]
    if _near_echo_without_value(text, query) or _negative_or_inferential(text):
        return None

    query_relations = relation_concepts(query)
    memory_relations = relation_concepts(text)
    if query_relations and not (query_relations & memory_relations):
        return None

    anchors = _entity_anchors(query)
    lowered = text.casefold()
    if anchors and not all(anchor in lowered for anchor in anchors):
        return None

    values = _asserted_value_tokens(text, query)
    if not values:
        return None

    stems = {_stem(token) for token in tokens(text)}
    return EvidenceProposition(
        memory_id=memory["id"],
        relations=frozenset(memory_relations),
        values=frozenset(values),
        timestamp=parse_timestamp(memory.get("timestamp")),
        stale=bool(stems & STALE_STEMS),
        resolving=bool(stems & RESOLUTION_STEMS),
    )


def _required_relations(query: str) -> list[str]:
    relations = sorted(relation_concepts(query))
    return relations or ["generic"]


def answerability_signature(case: dict[str, Any], ranking: list[str] | None = None) -> dict[str, Any]:
    ranking = ranking if ranking is not None else pse_candidate_v2_rank(case, 5)
    by_id = {memory["id"]: memory for memory in case["memories"]}
    requirements = _required_relations(case["query"])
    coverage: dict[str, list[EvidenceProposition]] = {requirement: [] for requirement in requirements}

    for memory_id in ranking:
        memory = by_id.get(memory_id)
        if memory is None:
            continue
        proposition = _parse_proposition(memory, case["query"])
        if proposition is None:
            continue
        for requirement in requirements:
            if requirement == "generic" or requirement in proposition.relations:
                coverage[requirement].append(proposition)

    current_query = bool({_stem(token) for token in tokens(case["query"])} & QUERY_TIME_STEMS)
    if current_query:
        for requirement, propositions in coverage.items():
            coverage[requirement] = [
                proposition
                for proposition in propositions
                if (not proposition.stale) or proposition.resolving
            ]

    missing = [requirement for requirement, propositions in coverage.items() if not propositions]
    if missing:
        return {
            "verdict": VERDICT_INSUFFICIENT,
            "requirements": requirements,
            "missing_requirements": missing,
            "coverage": {key: [p.memory_id for p in value] for key, value in coverage.items()},
        }

    selected: dict[str, list[EvidenceProposition]] = {}
    for requirement, propositions in coverage.items():
        resolving = [proposition for proposition in propositions if proposition.resolving]
        if resolving:
            latest_time = max(proposition.timestamp for proposition in resolving)
            latest = [proposition for proposition in resolving if proposition.timestamp == latest_time]
            if len(latest) != 1:
                return {
                    "verdict": VERDICT_AMIGUOUS,
                    "requirements": requirements,
                    "missing_requirements": [],
                    "coverage": {key: [p.memory_id for p in value] for key, value in coverage.items()},
                    "ambiguous_requirement": requirement,
                }
            selected[requirement] = latest
            continue

        if len(propositions) > 1:
            value_sets = [set(proposition.values) for proposition in propositions]
            if value_sets and not set.intersection(*value_sets):
                return {
                    "verdict": VERDICT_CONTRADICTED,
                    "requirements": requirements,
                    "missing_requirements": [],
                    "coverage": {key: [p.memory_id for p in value] for key, value in coverage.items()},
                    "contradicted_requirement": requirement,
                }
        selected[requirement] = propositions

    return {
        "verdict": VERDICT_SUPPORTED,
        "requirements": requirements,
        "missing_requirements": [],
        "coverage": {key: [p.memory_id for p in value] for key, value in selected.items()},
    }


def pse_candidate_v5_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    """Frozen Candidate-v2 retrieval plus an independent evidence-graph gate."""
    ranking = pse_candidate_v2_rank(case, k)
    signature = answerability_signature(case, ranking)
    return ranking if signature["verdict"] == VERDICT_SUPPORTED else []
