from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


class TrialRecordError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TrialRecord:
    trial_id: str
    baseline: str
    scenario_id: str
    split: str
    model_provider: str
    model_id: str
    model_version: str
    seed: int | None
    repetition: int
    status: str
    passed: bool | None
    latency_ms: float
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float | None
    output_text: str | None
    error_type: str | None = None

    def validate(self) -> None:
        if not self.trial_id or not self.scenario_id:
            raise TrialRecordError("trial and scenario identifiers are required")
        if self.split not in {"development", "validation", "final_test", "pilot_test"}:
            raise TrialRecordError(f"invalid split: {self.split}")
        if self.status not in {"completed", "error", "timeout", "skipped"}:
            raise TrialRecordError(f"invalid status: {self.status}")
        if self.status == "completed" and self.passed is None:
            raise TrialRecordError("completed trials require a score")
        if self.repetition < 0 or self.latency_ms < 0:
            raise TrialRecordError("repetition and latency must be non-negative")
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise TrialRecordError("token counts must be non-negative")
        if not self.model_version or self.model_version.upper().startswith("PIN_"):
            raise TrialRecordError("exact model version is required")


def write_trials(records: list[TrialRecord], path: str | Path) -> Path:
    seen: set[str] = set()
    rows: list[str] = []
    for record in records:
        record.validate()
        if record.trial_id in seen:
            raise TrialRecordError(f"duplicate trial id: {record.trial_id}")
        seen.add(record.trial_id)
        rows.append(json.dumps(asdict(record), sort_keys=True, ensure_ascii=False))
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    return destination


def read_trials(path: str | Path) -> list[TrialRecord]:
    records: list[TrialRecord] = []
    seen: set[str] = set()
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = TrialRecord(**json.loads(line))
            record.validate()
        except (TypeError, json.JSONDecodeError, TrialRecordError) as exc:
            raise TrialRecordError(f"line {line_number}: {exc}") from exc
        if record.trial_id in seen:
            raise TrialRecordError(f"line {line_number}: duplicate trial id {record.trial_id}")
        seen.add(record.trial_id)
        records.append(record)
    return records
