from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence


class LongMemEvalFormatError(ValueError):
    pass


QUESTION_TYPES = frozenset(
    {
        "single-session-user",
        "single-session-assistant",
        "single-session-preference",
        "temporal-reasoning",
        "knowledge-update",
        "multi-session",
    }
)


@dataclass(frozen=True, slots=True)
class LongMemEvalTurn:
    role: str
    content: str
    has_answer: bool = False


@dataclass(frozen=True, slots=True)
class LongMemEvalSession:
    session_id: str
    timestamp: str
    turns: tuple[LongMemEvalTurn, ...]


@dataclass(frozen=True, slots=True)
class LongMemEvalExample:
    question_id: str
    question_type: str
    question: str
    answer: object
    question_date: str
    sessions: tuple[LongMemEvalSession, ...]
    answer_session_ids: tuple[str, ...]

    @property
    def is_abstention(self) -> bool:
        return self.question_id.endswith("_abs")


@dataclass(frozen=True, slots=True)
class LongMemEvalHypothesis:
    question_id: str
    hypothesis: str


def _required_string(row: Mapping[str, object], field: str, *, location: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise LongMemEvalFormatError(f"{location}.{field} must be a non-blank string")
    return value


def _load_json_or_jsonl(path: str | Path) -> list[object]:
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise LongMemEvalFormatError(f"unable to read {source}") from exc
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        rows: list[object] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise LongMemEvalFormatError(
                    f"{source}: invalid JSON on line {line_number}"
                ) from exc
        return rows
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        return [parsed]
    raise LongMemEvalFormatError(f"{source}: JSON root must be an array or object")


def _parse_turn(raw: object, *, location: str) -> LongMemEvalTurn:
    if not isinstance(raw, Mapping):
        raise LongMemEvalFormatError(f"{location} must be an object")
    unexpected = set(raw).difference({"role", "content", "has_answer"})
    if unexpected:
        raise LongMemEvalFormatError(
            f"{location} has unexpected fields: {sorted(unexpected)}"
        )
    role = raw.get("role")
    content = raw.get("content")
    has_answer = raw.get("has_answer", False)
    if role not in {"user", "assistant"}:
        raise LongMemEvalFormatError(f"{location}.role must be user or assistant")
    if not isinstance(content, str):
        raise LongMemEvalFormatError(f"{location}.content must be a string")
    if not isinstance(has_answer, bool):
        raise LongMemEvalFormatError(f"{location}.has_answer must be boolean")
    return LongMemEvalTurn(role=role, content=content, has_answer=has_answer)


def parse_longmemeval_example(raw: object, *, index: int) -> LongMemEvalExample:
    location = f"examples[{index}]"
    if not isinstance(raw, Mapping):
        raise LongMemEvalFormatError(f"{location} must be an object")
    required = {
        "question_id",
        "question_type",
        "question",
        "answer",
        "question_date",
        "haystack_session_ids",
        "haystack_dates",
        "haystack_sessions",
        "answer_session_ids",
    }
    missing = required.difference(raw)
    if missing:
        raise LongMemEvalFormatError(f"{location} missing fields: {sorted(missing)}")

    question_id = _required_string(raw, "question_id", location=location)
    question_type = _required_string(raw, "question_type", location=location)
    if question_type not in QUESTION_TYPES:
        raise LongMemEvalFormatError(
            f"{location}.question_type is unsupported: {question_type}"
        )
    question = _required_string(raw, "question", location=location)
    question_date = _required_string(raw, "question_date", location=location)

    session_ids = raw["haystack_session_ids"]
    dates = raw["haystack_dates"]
    sessions = raw["haystack_sessions"]
    answer_ids = raw["answer_session_ids"]
    arrays = (session_ids, dates, sessions, answer_ids)
    if not all(
        isinstance(value, Sequence) and not isinstance(value, (str, bytes))
        for value in arrays
    ):
        raise LongMemEvalFormatError(
            f"{location}: session and answer fields must be arrays"
        )
    if not (len(session_ids) == len(dates) == len(sessions)):
        raise LongMemEvalFormatError(
            f"{location}: session ids, dates and contents must align"
        )
    if len(set(session_ids)) != len(session_ids):
        raise LongMemEvalFormatError(f"{location}: duplicate session ids")
    if not all(isinstance(item, str) and item.strip() for item in session_ids):
        raise LongMemEvalFormatError(
            f"{location}.haystack_session_ids must contain strings"
        )
    if not all(isinstance(item, str) and item.strip() for item in dates):
        raise LongMemEvalFormatError(
            f"{location}.haystack_dates must contain strings"
        )
    if not all(isinstance(item, str) and item.strip() for item in answer_ids):
        raise LongMemEvalFormatError(
            f"{location}.answer_session_ids must contain strings"
        )
    missing_evidence = set(answer_ids).difference(session_ids)
    if missing_evidence:
        raise LongMemEvalFormatError(
            f"{location}: answer sessions absent from history: {sorted(missing_evidence)}"
        )

    parsed_sessions: list[LongMemEvalSession] = []
    for session_index, (session_id, timestamp, raw_turns) in enumerate(
        zip(session_ids, dates, sessions, strict=True)
    ):
        if not isinstance(raw_turns, Sequence) or isinstance(raw_turns, (str, bytes)):
            raise LongMemEvalFormatError(
                f"{location}.haystack_sessions[{session_index}] must be an array"
            )
        turns = tuple(
            _parse_turn(
                turn,
                location=(
                    f"{location}.haystack_sessions[{session_index}]"
                    f"[{turn_index}]"
                ),
            )
            for turn_index, turn in enumerate(raw_turns)
        )
        parsed_sessions.append(
            LongMemEvalSession(
                session_id=session_id,
                timestamp=timestamp,
                turns=turns,
            )
        )

    return LongMemEvalExample(
        question_id=question_id,
        question_type=question_type,
        question=question,
        answer=raw["answer"],
        question_date=question_date,
        sessions=tuple(parsed_sessions),
        answer_session_ids=tuple(answer_ids),
    )


def load_longmemeval(path: str | Path) -> tuple[LongMemEvalExample, ...]:
    examples: list[LongMemEvalExample] = []
    seen: set[str] = set()
    for index, raw in enumerate(_load_json_or_jsonl(path)):
        example = parse_longmemeval_example(raw, index=index)
        if example.question_id in seen:
            raise LongMemEvalFormatError(
                f"duplicate question_id: {example.question_id}"
            )
        seen.add(example.question_id)
        examples.append(example)
    if not examples:
        raise LongMemEvalFormatError("dataset is empty")
    return tuple(examples)


def iter_history_turns(
    example: LongMemEvalExample,
    *,
    include_assistant: bool = True,
) -> Iterator[tuple[str, str, LongMemEvalTurn]]:
    for session in example.sessions:
        for turn in session.turns:
            if include_assistant or turn.role == "user":
                yield session.session_id, session.timestamp, turn


def render_history_json(
    example: LongMemEvalExample,
    *,
    include_assistant: bool = True,
    max_sessions: int | None = None,
) -> str:
    if max_sessions is not None and max_sessions <= 0:
        raise ValueError("max_sessions must be positive")
    selected = (
        example.sessions if max_sessions is None else example.sessions[-max_sessions:]
    )
    payload = []
    for session in selected:
        messages = [
            {"role": turn.role, "content": turn.content}
            for turn in session.turns
            if include_assistant or turn.role == "user"
        ]
        payload.append(
            {
                "session_id": session.session_id,
                "timestamp": session.timestamp,
                "messages": messages,
            }
        )
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def load_hypotheses(path: str | Path) -> tuple[LongMemEvalHypothesis, ...]:
    hypotheses: list[LongMemEvalHypothesis] = []
    seen: set[str] = set()
    for index, raw in enumerate(_load_json_or_jsonl(path)):
        if not isinstance(raw, Mapping):
            raise LongMemEvalFormatError(f"hypotheses[{index}] must be an object")
        location = f"hypotheses[{index}]"
        question_id = _required_string(raw, "question_id", location=location)
        hypothesis = _required_string(raw, "hypothesis", location=location)
        if question_id in seen:
            raise LongMemEvalFormatError(
                f"duplicate hypothesis question_id: {question_id}"
            )
        seen.add(question_id)
        hypotheses.append(LongMemEvalHypothesis(question_id, hypothesis))
    return tuple(hypotheses)


def write_hypotheses(
    hypotheses: Iterable[LongMemEvalHypothesis], path: str | Path
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    with destination.open("w", encoding="utf-8") as handle:
        for hypothesis in hypotheses:
            if hypothesis.question_id in seen:
                raise LongMemEvalFormatError(
                    f"duplicate hypothesis question_id: {hypothesis.question_id}"
                )
            if not hypothesis.question_id.strip() or not hypothesis.hypothesis.strip():
                raise LongMemEvalFormatError("hypothesis fields must be non-blank")
            seen.add(hypothesis.question_id)
            handle.write(
                json.dumps(
                    {
                        "question_id": hypothesis.question_id,
                        "hypothesis": hypothesis.hypothesis,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
    return destination
