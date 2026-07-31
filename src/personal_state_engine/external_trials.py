from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from .longmemeval import LongMemEvalExample, LongMemEvalSession
from .model_adapters import ModelAdapter, ModelAdapterError, ModelRequest, RunManifest


class ExternalTrialError(RuntimeError):
    pass


_TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)
_SUPPORTED_BASELINES = frozenset({"EXT-B0", "EXT-B5"})


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(payload)


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(token.casefold() for token in _TOKEN_RE.findall(text))


def _session_text(session: LongMemEvalSession) -> str:
    parts = [session.timestamp]
    parts.extend(f"{turn.role}: {turn.content}" for turn in session.turns)
    return "\n".join(parts)


def bm25_sessions(
    query: str,
    sessions: Sequence[LongMemEvalSession],
    *,
    k: int,
    k1: float = 1.2,
    b: float = 0.75,
) -> tuple[LongMemEvalSession, ...]:
    """Return a deterministic BM25 ranking with stable chronological tie-breaking."""
    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        raise ExternalTrialError("retrieval k must be a positive integer")
    if not sessions:
        return ()
    if not math.isfinite(k1) or k1 <= 0:
        raise ExternalTrialError("BM25 k1 must be finite and positive")
    if not math.isfinite(b) or not 0 <= b <= 1:
        raise ExternalTrialError("BM25 b must be finite and between 0 and 1")

    documents = [_tokens(_session_text(session)) for session in sessions]
    query_tokens = _tokens(query)
    if not query_tokens:
        return tuple(sessions[-k:])
    average_length = sum(len(document) for document in documents) / len(documents)
    document_frequency: dict[str, int] = {}
    for token in set(query_tokens):
        document_frequency[token] = sum(token in document for document in documents)

    scored: list[tuple[float, int, LongMemEvalSession]] = []
    count = len(documents)
    for index, (session, document) in enumerate(zip(sessions, documents, strict=True)):
        frequencies: dict[str, int] = {}
        for token in document:
            frequencies[token] = frequencies.get(token, 0) + 1
        score = 0.0
        for token in query_tokens:
            frequency = frequencies.get(token, 0)
            if frequency == 0:
                continue
            df = document_frequency[token]
            inverse_document_frequency = math.log(1 + (count - df + 0.5) / (df + 0.5))
            denominator = frequency + k1 * (
                1 - b + b * len(document) / max(average_length, 1.0)
            )
            score += inverse_document_frequency * frequency * (k1 + 1) / denominator
        scored.append((score, index, session))

    ranked = sorted(scored, key=lambda item: (-item[0], item[1]))[: min(k, len(scored))]
    return tuple(item[2] for item in ranked)


def _render_sessions(sessions: Iterable[LongMemEvalSession]) -> str:
    blocks: list[str] = []
    for session in sessions:
        lines = [f"Session {session.session_id} at {session.timestamp}"]
        lines.extend(f"{turn.role}: {turn.content}" for turn in session.turns)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


@dataclass(frozen=True, slots=True)
class ExternalTrialConfig:
    run_id: str
    dataset_name: str
    dataset_version: str
    dataset_sha256: str
    split_name: str
    split_manifest_sha256: str
    baseline_id: str
    baseline_version: str
    retrieval_item_limit: int = 5
    retrieval_token_budget: int = 4096
    memory_token_budget: int = 4096
    prompt_template_version: str = "longmemeval-answer-v1"
    evaluator_id: str = "unscored"
    evaluator_version: str = "unscored-v1"
    code_commit: str = "UNCOMMITTED"
    environment_manifest_sha256: str = "UNAVAILABLE"

    def validate(self) -> None:
        required = {
            "run_id": self.run_id,
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "dataset_sha256": self.dataset_sha256,
            "split_name": self.split_name,
            "split_manifest_sha256": self.split_manifest_sha256,
            "baseline_version": self.baseline_version,
            "prompt_template_version": self.prompt_template_version,
            "evaluator_id": self.evaluator_id,
            "evaluator_version": self.evaluator_version,
            "code_commit": self.code_commit,
            "environment_manifest_sha256": self.environment_manifest_sha256,
        }
        for field, value in required.items():
            if not isinstance(value, str) or not value.strip():
                raise ExternalTrialError(f"{field} must be a non-blank string")
        if self.baseline_id not in _SUPPORTED_BASELINES:
            raise ExternalTrialError(f"unsupported external baseline: {self.baseline_id}")
        for field, value in (
            ("retrieval_item_limit", self.retrieval_item_limit),
            ("retrieval_token_budget", self.retrieval_token_budget),
            ("memory_token_budget", self.memory_token_budget),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ExternalTrialError(f"{field} must be a positive integer")


@dataclass(frozen=True, slots=True)
class ExternalTrialRecord:
    schema_version: str
    trial_id: str
    run_id: str
    request_id: str
    dataset_name: str
    dataset_version: str
    dataset_sha256: str
    split_name: str
    split_manifest_sha256: str
    case_id: str
    conversation_id: str
    question_type: str
    baseline_id: str
    baseline_version: str
    model_provider: str
    model_id: str
    model_revision: str
    tokenizer_id: str
    tokenizer_revision: str
    runtime_name: str
    runtime_version: str
    quantization: str
    hardware: str
    seed: int | None
    temperature: float
    top_p: float
    max_output_tokens: int
    context_limit: int
    retrieval_item_limit: int
    retrieval_token_budget: int
    memory_token_budget: int
    timeout_seconds: float
    retry_policy: str
    prompt_template_version: str
    prompt_sha256: str
    retrieved_items: tuple[str, ...]
    retrieval_scores: tuple[float, ...]
    retrieval_timestamps: tuple[str, ...]
    raw_prompt_or_reconstruction_fields: dict[str, object]
    raw_model_output: dict[str, object] | None
    parsed_answer: str | None
    reference_answer: object
    evaluator_id: str
    evaluator_version: str
    evaluator_output: dict[str, object] | None
    human_audit_status: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    ingestion_tokens: int
    retrieval_tokens: int
    summary_tokens: int
    latency_ms: float
    estimated_cost: float | None
    storage_bytes: int
    error_type: str | None
    error_message: str | None
    attempt_number: int
    code_commit: str
    configuration_sha256: str
    environment_manifest_sha256: str
    started_at: str
    completed_at: str
    status: str

    def validate(self) -> None:
        identifiers = (
            self.schema_version,
            self.trial_id,
            self.run_id,
            self.request_id,
            self.dataset_name,
            self.dataset_version,
            self.dataset_sha256,
            self.split_name,
            self.split_manifest_sha256,
            self.case_id,
            self.conversation_id,
            self.question_type,
            self.baseline_id,
            self.baseline_version,
            self.model_provider,
            self.model_id,
            self.model_revision,
            self.prompt_template_version,
            self.prompt_sha256,
            self.evaluator_id,
            self.evaluator_version,
            self.human_audit_status,
            self.retry_policy,
            self.code_commit,
            self.configuration_sha256,
            self.environment_manifest_sha256,
            self.started_at,
            self.completed_at,
            self.status,
        )
        if any(not isinstance(value, str) or not value.strip() for value in identifiers):
            raise ExternalTrialError("trial identifiers and provenance fields must be non-blank")
        if self.baseline_id not in _SUPPORTED_BASELINES:
            raise ExternalTrialError("trial baseline is unsupported")
        if self.status not in {"completed", "error", "timeout"}:
            raise ExternalTrialError("trial status is invalid")
        integer_fields = (
            self.max_output_tokens,
            self.context_limit,
            self.retrieval_item_limit,
            self.retrieval_token_budget,
            self.memory_token_budget,
            self.input_tokens,
            self.output_tokens,
            self.total_tokens,
            self.ingestion_tokens,
            self.retrieval_tokens,
            self.summary_tokens,
            self.storage_bytes,
            self.attempt_number,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in integer_fields):
            raise ExternalTrialError("trial integer accounting fields must be non-negative integers")
        if self.attempt_number < 1:
            raise ExternalTrialError("attempt_number must be at least one")
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ExternalTrialError("total_tokens must equal input_tokens plus output_tokens")
        if not math.isfinite(self.latency_ms) or self.latency_ms < 0:
            raise ExternalTrialError("latency_ms must be finite and non-negative")
        if self.estimated_cost is not None and (
            not math.isfinite(self.estimated_cost) or self.estimated_cost < 0
        ):
            raise ExternalTrialError("estimated_cost must be finite and non-negative")
        if self.status == "completed" and self.parsed_answer is None:
            raise ExternalTrialError("completed trial requires parsed_answer")
        if self.status != "completed" and not self.error_type:
            raise ExternalTrialError("failed trial requires error_type")

    def as_json(self) -> str:
        self.validate()
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


def build_request(
    example: LongMemEvalExample,
    manifest: RunManifest,
    config: ExternalTrialConfig,
    *,
    request_id: str,
) -> tuple[ModelRequest, tuple[LongMemEvalSession, ...], dict[str, object]]:
    config.validate()
    if config.baseline_id == "EXT-B0":
        selected: tuple[LongMemEvalSession, ...] = ()
    else:
        selected = bm25_sessions(
            example.question,
            example.sessions,
            k=config.retrieval_item_limit,
        )

    history = _render_sessions(selected)
    system_prompt = (
        "Answer the user's question using only the supplied conversation history. "
        "If the history is insufficient, say that the answer is unknown. "
        "Return only the answer, without explaining the retrieval method."
    )
    user_content = f"Question date: {example.question_date}\nQuestion: {example.question}"
    if history:
        user_content = f"Conversation history:\n{history}\n\n{user_content}"
    reconstruction = {
        "system_prompt": system_prompt,
        "question": example.question,
        "question_date": example.question_date,
        "selected_session_ids": [session.session_id for session in selected],
        "selected_session_timestamps": [session.timestamp for session in selected],
        "history": history,
    }
    request = ModelRequest(
        request_id=request_id,
        system_prompt=system_prompt,
        messages=({"role": "user", "content": user_content},),
        manifest=manifest,
    )
    return request, selected, reconstruction


def execute_trial(
    example: LongMemEvalExample,
    manifest: RunManifest,
    config: ExternalTrialConfig,
    adapter: ModelAdapter,
    *,
    trial_id: str | None = None,
    request_id: str | None = None,
    attempt_number: int = 1,
    now: Callable[[], float] = time.time,
) -> ExternalTrialRecord:
    config.validate()
    trial_id = trial_id or str(uuid.uuid4())
    request_id = request_id or f"{config.run_id}:{example.question_id}:{trial_id}"
    request, selected, reconstruction = build_request(
        example,
        manifest,
        config,
        request_id=request_id,
    )
    configuration_sha256 = canonical_sha256(
        {"manifest": asdict(manifest), "config": asdict(config)}
    )
    prompt_sha256 = canonical_sha256(reconstruction)
    started_epoch = now()
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started_epoch))
    response = None
    error_type = None
    error_message = None
    status = "completed"
    try:
        response = adapter.complete(request)
    except ModelAdapterError as exc:
        error_type = type(exc).__name__
        error_message = str(exc)
        status = "timeout" if "timed out" in str(exc).lower() else "error"
    completed_epoch = now()
    completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(completed_epoch))
    observed_latency = max(0.0, (completed_epoch - started_epoch) * 1000)

    usage = response.usage if response is not None else {}
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    latency_ms = response.latency_ms if response is not None else observed_latency
    raw_output = response.raw if response is not None else None
    parsed_answer = response.text if response is not None else None
    storage_bytes = (
        len(json.dumps(raw_output, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        if raw_output is not None
        else 0
    )

    record = ExternalTrialRecord(
        schema_version="external-trial-v1",
        trial_id=trial_id,
        run_id=config.run_id,
        request_id=request_id,
        dataset_name=config.dataset_name,
        dataset_version=config.dataset_version,
        dataset_sha256=config.dataset_sha256,
        split_name=config.split_name,
        split_manifest_sha256=config.split_manifest_sha256,
        case_id=example.question_id,
        conversation_id=example.question_id,
        question_type=example.question_type,
        baseline_id=config.baseline_id,
        baseline_version=config.baseline_version,
        model_provider=manifest.model_provider,
        model_id=manifest.model_id,
        model_revision=manifest.model_version,
        tokenizer_id="provider-reported-or-unavailable",
        tokenizer_revision="provider-reported-or-unavailable",
        runtime_name="subprocess-or-replay-adapter",
        runtime_version="external-adapter-v1",
        quantization="provider-reported-or-unavailable",
        hardware="provider-reported-or-unavailable",
        seed=manifest.seed,
        temperature=float(manifest.temperature),
        top_p=1.0,
        max_output_tokens=manifest.token_budget,
        context_limit=config.retrieval_token_budget + config.memory_token_budget,
        retrieval_item_limit=config.retrieval_item_limit,
        retrieval_token_budget=config.retrieval_token_budget,
        memory_token_budget=config.memory_token_budget,
        timeout_seconds=float(manifest.timeout_seconds),
        retry_policy="no-automatic-retry",
        prompt_template_version=config.prompt_template_version,
        prompt_sha256=prompt_sha256,
        retrieved_items=tuple(session.session_id for session in selected),
        retrieval_scores=(),
        retrieval_timestamps=tuple(session.timestamp for session in selected),
        raw_prompt_or_reconstruction_fields=reconstruction,
        raw_model_output=raw_output,
        parsed_answer=parsed_answer,
        reference_answer=example.answer,
        evaluator_id=config.evaluator_id,
        evaluator_version=config.evaluator_version,
        evaluator_output=None,
        human_audit_status="not-audited",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        ingestion_tokens=0,
        retrieval_tokens=0,
        summary_tokens=0,
        latency_ms=latency_ms,
        estimated_cost=None,
        storage_bytes=storage_bytes,
        error_type=error_type,
        error_message=error_message,
        attempt_number=attempt_number,
        code_commit=config.code_commit,
        configuration_sha256=configuration_sha256,
        environment_manifest_sha256=config.environment_manifest_sha256,
        started_at=started_at,
        completed_at=completed_at,
        status=status,
    )
    record.validate()
    return record


def write_immutable_trial(record: ExternalTrialRecord, output_directory: str | Path) -> Path:
    record.validate()
    destination = Path(output_directory)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"{record.trial_id}.json"
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ExternalTrialError(f"trial output already exists: {path}") from exc
    try:
        payload = (record.as_json() + "\n").encode("utf-8")
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path
