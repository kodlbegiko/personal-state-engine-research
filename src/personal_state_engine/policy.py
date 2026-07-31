from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .models import MemoryKind, MemoryRecord, SourceType


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    reasons: tuple[str, ...]


def normalize_for_detection(value: str) -> str:
    """Normalize Unicode and remove format controls before safety matching."""
    normalized = unicodedata.normalize("NFKC", value)
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Cf")
    return " ".join(normalized.casefold().split())


class MemoryWritePolicy:
    """Conservative minimum policy for durable memory writes.

    The rules are deterministic and intentionally fail closed for high-signal
    durable-instruction and credential patterns. They are not a complete prompt
    injection detector and must be evaluated for false positives.
    """

    _injection_patterns = (
        re.compile(
            r"\b(ignore|disregard|forget|override)\b.{0,40}"
            r"\b(previous|prior|earlier)\b.{0,24}\b(instructions?|rules?|prompts?)\b",
            re.I,
        ),
        re.compile(
            r"\b(store|remember|save|persist)\b.{0,30}\b(this|the following)\b"
            r".{0,20}\b(instruction(?!\s+manual)|rule|prompt)\b",
            re.I,
        ),
        re.compile(
            r"\b(reveal|show|print|leak|store|remember)\b.{0,30}\bsystem prompt\b",
            re.I,
        ),
        re.compile(r"(?:忽略|無視|忘掉|覆蓋).{0,20}(?:先前|之前|原本).{0,12}(?:指令|規則|提示)"),
        re.compile(r"(?:永久|永遠).{0,10}(?:記住|保存).{0,20}(?:指令|規則|提示)"),
        re.compile(r"以前の.{0,12}(?:指示|命令).{0,12}(?:無視|忘れ)"),
        re.compile(r"이전.{0,12}(?:지시|명령).{0,12}(?:무시|잊어)"),
    )
    _secret_patterns = (
        re.compile(r"\bsk-[a-z0-9_-]{12,}\b", re.I),
        re.compile(r"\bgh[pousr]_[a-z0-9]{20,}\b", re.I),
        re.compile(r"\bbearer\s+[a-z0-9._~+/=-]{20,}\b", re.I),
        re.compile(r"\beyj[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}\b", re.I),
        re.compile(r"\b(password|passwd|api[_ -]?key|access[_ -]?token)\s*[:=]", re.I),
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    )

    def evaluate(self, record: MemoryRecord) -> PolicyDecision:
        reasons: list[str] = []
        content = record.content.strip()
        normalized = normalize_for_detection(content)
        if not content:
            reasons.append("empty_content")
        if not 0.0 <= record.confidence <= 1.0:
            reasons.append("invalid_confidence")
        if record.provenance.source_type is SourceType.MODEL_INFERRED:
            if record.kind is MemoryKind.SEMANTIC and record.provenance.allow_long_term:
                reasons.append("model_inference_cannot_be_durable_semantic_fact")
        if record.provenance.sensitive and not record.provenance.allow_long_term:
            reasons.append("sensitive_long_term_storage_not_allowed")
        if any(pattern.search(normalized) for pattern in self._injection_patterns):
            reasons.append("possible_memory_prompt_injection")
        if any(pattern.search(normalized) for pattern in self._secret_patterns):
            reasons.append("possible_secret_or_credential")
        return PolicyDecision(allowed=not reasons, reasons=tuple(dict.fromkeys(reasons)))
