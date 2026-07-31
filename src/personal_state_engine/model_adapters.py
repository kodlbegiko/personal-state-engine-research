from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol


class ModelAdapterError(RuntimeError):
    pass


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

    @classmethod
    def from_json(cls, path: str | Path) -> "RunManifest":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
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
        manifest = cls(**{field: data[field] for field in required})
        if not 0 <= manifest.temperature <= 2:
            raise ModelAdapterError("temperature must be between 0 and 2")
        if manifest.token_budget <= 0 or manifest.timeout_seconds <= 0:
            raise ModelAdapterError("token budget and timeout must be positive")
        return manifest


@dataclass(frozen=True, slots=True)
class ModelRequest:
    request_id: str
    system_prompt: str
    messages: tuple[dict[str, str], ...]
    manifest: RunManifest


@dataclass(frozen=True, slots=True)
class ModelResponse:
    request_id: str
    text: str
    usage: dict[str, int]
    latency_ms: float
    raw: dict[str, object]


class ModelAdapter(Protocol):
    def complete(self, request: ModelRequest) -> ModelResponse: ...


class ReplayAdapter:
    """Deterministic adapter for reproducing previously captured model outputs."""

    def __init__(self, responses: dict[str, ModelResponse]) -> None:
        self.responses = responses

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "ReplayAdapter":
        responses: dict[str, ModelResponse] = {}
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            response = ModelResponse(
                request_id=row["request_id"],
                text=row["text"],
                usage=row.get("usage", {}),
                latency_ms=float(row.get("latency_ms", 0.0)),
                raw=row,
            )
            if response.request_id in responses:
                raise ModelAdapterError(f"duplicate replay response: {response.request_id}")
            responses[response.request_id] = response
        return cls(responses)

    def complete(self, request: ModelRequest) -> ModelResponse:
        try:
            return self.responses[request.request_id]
        except KeyError as exc:
            raise ModelAdapterError(f"missing replay response: {request.request_id}") from exc


class SubprocessJSONAdapter:
    """Provider-neutral adapter using one JSON request/response over stdio."""

    def __init__(self, command: list[str]) -> None:
        if not command:
            raise ModelAdapterError("adapter command is required")
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
            return ModelResponse(
                request_id=row["request_id"],
                text=row["text"],
                usage=row.get("usage", {}),
                latency_ms=float(row.get("latency_ms", 0.0)),
                raw=row,
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ModelAdapterError("adapter returned malformed JSON") from exc
