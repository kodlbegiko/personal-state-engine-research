from __future__ import annotations

import json
import math
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol


class ModelAdapterError(RuntimeError):
    pass


_PLACEHOLDER_VALUES = {
    "REPLACE_ME",
    "REPLACEME",
    "TODO",
    "TBD",
    "UNKNOWN",
    "UNSET",
    "CHANGEME",
}


def _validated_identifier(field: str, value: object) -> str:
    if not isinstance(value, str):
        raise ModelAdapterError(f"{field} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ModelAdapterError(f"{field} must not be blank")
    marker = normalized.upper().replace("-", "_").replace(" ", "_")
    if (
        marker in _PLACEHOLDER_VALUES
        or marker.startswith("PIN_")
        or marker.startswith("REPLACE_")
        or "{{" in normalized
        or "}}" in normalized
        or "<" in normalized
        or ">" in normalized
    ):
        raise ModelAdapterError(f"{field} contains a placeholder value")
    return normalized


def _validated_usage(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        raise ModelAdapterError("usage must be an object")
    validated: dict[str, int] = {}
    for key, count in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ModelAdapterError("usage keys must be non-blank strings")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ModelAdapterError(f"usage[{key!r}] must be a non-negative integer")
        validated[key] = count
    return validated


def _validated_non_negative_number(field: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ModelAdapterError(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ModelAdapterError(f"{field} must be finite and non-negative")
    return number


@dataclass(frozen=True, slots=True)
class RunManifest:
    model_provider: str
    model_id: str
    model_version: str
    temperature: float
    seed: int | None
    token_budget: int
    timeout_seconds: float
    tool_policy: str

    def __post_init__(self) -> None:
        _validated_identifier("model_provider", self.model_provider)
        _validated_identifier("model_id", self.model_id)
        _validated_identifier("model_version", self.model_version)
        _validated_identifier("tool_policy", self.tool_policy)
        if isinstance(self.temperature, bool) or not isinstance(self.temperature, (int, float)):
            raise ModelAdapterError("temperature must be numeric")
        temperature = float(self.temperature)
        if not math.isfinite(temperature) or not 0 <= temperature <= 2:
            raise ModelAdapterError("temperature must be finite and between 0 and 2")
        if self.seed is not None and (isinstance(self.seed, bool) or not isinstance(self.seed, int)):
            raise ModelAdapterError("seed must be an integer or null")
        if isinstance(self.token_budget, bool) or not isinstance(self.token_budget, int):
            raise ModelAdapterError("token_budget must be an integer")
        if self.token_budget <= 0:
            raise ModelAdapterError("token_budget must be positive")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)):
            raise ModelAdapterError("timeout_seconds must be numeric")
        timeout = float(self.timeout_seconds)
        if not math.isfinite(timeout) or timeout <= 0:
            raise ModelAdapterError("timeout_seconds must be finite and positive")

    @classmethod
    def from_json(cls, path: str | Path) -> "RunManifest":
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ModelAdapterError("manifest is not readable valid JSON") from exc
        if not isinstance(data, dict):
            raise ModelAdapterError("manifest root must be an object")
        required = {
            "model_provider",
            "model_id",
            "model_version",
            "temperature",
            "seed",
            "token_budget",
            "timeout_seconds",
            "tool_policy",
        }
        missing = required.difference(data)
        if missing:
            raise ModelAdapterError(f"manifest missing fields: {sorted(missing)}")
        unexpected = set(data).difference(required)
        if unexpected:
            raise ModelAdapterError(f"manifest has unexpected fields: {sorted(unexpected)}")
        try:
            return cls(**{field: data[field] for field in required})
        except TypeError as exc:
            raise ModelAdapterError("manifest field types are invalid") from exc


@dataclass(frozen=True, slots=True)
class ModelRequest:
    request_id: str
    system_prompt: str
    messages: tuple[dict[str, str], ...]
    manifest: RunManifest

    def __post_init__(self) -> None:
        _validated_identifier("request_id", self.request_id)
        if not isinstance(self.system_prompt, str):
            raise ModelAdapterError("system_prompt must be a string")
        if not isinstance(self.messages, tuple):
            raise ModelAdapterError("messages must be a tuple")
        for index, message in enumerate(self.messages):
            if not isinstance(message, dict):
                raise ModelAdapterError(f"messages[{index}] must be an object")
            if set(message) != {"role", "content"}:
                raise ModelAdapterError(f"messages[{index}] must contain only role and content")
            if not all(isinstance(message[key], str) for key in ("role", "content")):
                raise ModelAdapterError(f"messages[{index}] role and content must be strings")


@dataclass(frozen=True, slots=True)
class ModelResponse:
    request_id: str
    text: str
    usage: dict[str, int]
    latency_ms: float
    raw: dict[str, object]

    def __post_init__(self) -> None:
        _validated_identifier("response request_id", self.request_id)
        if not isinstance(self.text, str):
            raise ModelAdapterError("response text must be a string")
        _validated_usage(self.usage)
        _validated_non_negative_number("latency_ms", self.latency_ms)
        if not isinstance(self.raw, dict):
            raise ModelAdapterError("raw response must be an object")


class ModelAdapter(Protocol):
    def complete(self, request: ModelRequest) -> ModelResponse: ...


class ReplayAdapter:
    """Deterministic adapter for reproducing previously captured model outputs."""

    def __init__(self, responses: dict[str, ModelResponse]) -> None:
        self.responses = responses

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "ReplayAdapter":
        responses: dict[str, ModelResponse] = {}
        for line_number, line in enumerate(
            Path(path).read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                response = ModelResponse(
                    request_id=row["request_id"],
                    text=row["text"],
                    usage=row.get("usage", {}),
                    latency_ms=row.get("latency_ms", 0.0),
                    raw=row,
                )
            except (json.JSONDecodeError, KeyError, TypeError, ValueError, ModelAdapterError) as exc:
                raise ModelAdapterError(f"replay line {line_number} is invalid") from exc
            if response.request_id in responses:
                raise ModelAdapterError(f"duplicate replay response: {response.request_id}")
            responses[response.request_id] = response
        return cls(responses)

    def complete(self, request: ModelRequest) -> ModelResponse:
        try:
            response = self.responses[request.request_id]
        except KeyError as exc:
            raise ModelAdapterError(f"missing replay response: {request.request_id}") from exc
        if response.request_id != request.request_id:
            raise ModelAdapterError("replay response request_id mismatch")
        return response


class SubprocessJSONAdapter:
    """Provider-neutral adapter using one JSON request/response over stdio."""

    def __init__(self, command: list[str]) -> None:
        if not command or not all(isinstance(part, str) and part for part in command):
            raise ModelAdapterError("adapter command must contain non-blank strings")
        self.command = command

    def complete(self, request: ModelRequest) -> ModelResponse:
        payload = json.dumps(
            {
                "request_id": request.request_id,
                "system_prompt": request.system_prompt,
                "messages": request.messages,
                "manifest": asdict(request.manifest),
            }
        )
        try:
            completed = subprocess.run(
                self.command,
                input=payload,
                text=True,
                capture_output=True,
                timeout=request.manifest.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ModelAdapterError("adapter timed out") from exc
        if completed.returncode != 0:
            raise ModelAdapterError(
                f"adapter exited {completed.returncode}: {completed.stderr.strip()}"
            )
        try:
            row = json.loads(completed.stdout)
            if not isinstance(row, dict):
                raise TypeError("response root is not an object")
            response = ModelResponse(
                request_id=row["request_id"],
                text=row["text"],
                usage=row.get("usage", {}),
                latency_ms=row.get("latency_ms", 0.0),
                raw=row,
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, ModelAdapterError) as exc:
            raise ModelAdapterError("adapter returned malformed JSON") from exc
        if response.request_id != request.request_id:
            raise ModelAdapterError(
                f"adapter response request_id mismatch: expected {request.request_id!r}, "
                f"received {response.request_id!r}"
            )
        return response
