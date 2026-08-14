#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from personal_state_engine.longmemeval_evaluator import (
    LOCAL_FALLBACK_MODEL,
    LOCAL_FALLBACK_REVISION,
    OFFICIAL_OPENAI_MODEL,
    OFFICIAL_SOURCE_COMMIT,
    OFFICIAL_SOURCE_PATH,
    OFFICIAL_SOURCE_REPOSITORY,
    PROMPT_TEMPLATES,
    blinded_response_id,
    build_official_prompt,
    calculate_calibration,
    canonical_json,
    deterministic_case_mapping,
    load_trials,
    parse_strict_yes_no,
    prompt_templates_sha256,
    sha256_file,
    sha256_text,
    summarize_formal_results,
    verify_archive_registry,
)


class JudgeError(RuntimeError):
    pass


class LocalNodeJudge:
    def __init__(self, model_server: Path, cache_directory: Path, dtype: str = "q4") -> None:
        self.model_server = model_server
        self.cache_directory = cache_directory
        self.dtype = dtype
        self.process: subprocess.Popen[str] | None = None
        self.ready: dict[str, Any] | None = None

    def __enter__(self) -> "LocalNodeJudge":
        env = os.environ.copy()
        env.update(
            {
                "PSE_MODEL_ID": LOCAL_FALLBACK_MODEL,
                "PSE_MODEL_REVISION": LOCAL_FALLBACK_REVISION,
                "PSE_MODEL_DTYPE": self.dtype,
                "PSE_HF_CACHE": str(self.cache_directory),
            }
        )
        self.process = subprocess.Popen(
            ["node", str(self.model_server)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        assert self.process.stdout is not None
        ready_line = self.process.stdout.readline()
        if not ready_line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise JudgeError(f"local judge did not become ready: {stderr[-4000:]}")
        try:
            self.ready = json.loads(ready_line)
        except json.JSONDecodeError as exc:
            raise JudgeError(f"invalid local judge ready line: {ready_line!r}") from exc
        if self.ready.get("status") != "ready":
            raise JudgeError(f"local judge readiness failed: {self.ready}")
        return self

    def judge(self, request_id: str, prompt: str) -> dict[str, Any]:
        if self.process is None or self.process.stdin is None or self.process.stdout is None:
            raise JudgeError("local judge is not running")
        request = {
            "request_id": request_id,
            "system_prompt": "",
            "messages": [{"role": "user", "content": prompt}],
            "manifest": {"token_budget": 6},
        }
        self.process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise JudgeError(f"local judge stopped before response: {stderr[-4000:]}")
        response = json.loads(line)
        if response.get("error"):
            raise JudgeError(str(response["error"]))
        return response

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.process is None:
            return
        if self.process.stdin:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


class OpenAIJudge:
    def __init__(self) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise JudgeError("openai==1.35.1 is required for the official evaluator path") from exc
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise JudgeError("OPENAI_API_KEY is absent")
        self.client = OpenAI(api_key=api_key, organization=os.getenv("OPENAI_ORGANIZATION") or None)
        self.ready = {
            "status": "ready",
            "model_id": OFFICIAL_OPENAI_MODEL,
            "runtime": "openai-python",
            "runtime_version": "1.35.1",
        }

    def __enter__(self) -> "OpenAIJudge":
        return self

    def judge(self, request_id: str, prompt: str) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                started = time.perf_counter()
                completion = self.client.chat.completions.create(
                    model=OFFICIAL_OPENAI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    n=1,
                    temperature=0,
                    max_tokens=10,
                )
                latency_ms = (time.perf_counter() - started) * 1000
                usage = completion.usage
                return {
                    "request_id": request_id,
                    "text": completion.choices[0].message.content or "",
                    "latency_ms": latency_ms,
                    "usage": {
                        "input_tokens": int(usage.prompt_tokens) if usage else None,
                        "output_tokens": int(usage.completion_tokens) if usage else None,
                        "total_tokens": int(usage.total_tokens) if usage else None,
                    },
                    "model_id": completion.model,
                    "system_fingerprint": getattr(completion, "system_fingerprint", None),
                    "response_id": completion.id,
                    "retry_attempt": attempt,
                }
            except Exception as exc:  # provider errors are preserved; no output-based retry
                last_error = exc
                if attempt < 3:
                    time.sleep(2 ** (attempt - 1))
        raise JudgeError(f"official evaluator API failed after 3 attempts: {last_error}")

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        return None


def json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def jsonl_dump(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def copy_preserving(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def build_audit_rows(audit_file: Path, audit_key_file: Path) -> list[dict[str, Any]]:
    completed = json.loads(audit_file.read_text(encoding="utf-8"))
    key = json.loads(audit_key_file.read_text(encoding="utf-8"))
    mapping_by_case = {row["case_id"]: row["mapping"] for row in key["rows"]}
    rows: list[dict[str, Any]] = []
    for case in completed["rows"]:
        case_id = case["case_id"]
        mapping = mapping_by_case[case_id]
        for label, answer in case["answers"].items():
            rows.append(
                {
                    "case_id": case_id,
                    "baseline_id": mapping[label],
                    "old_blinded_label": label,
                    "human_decision": answer.get("human_decision"),
                    "human_label": (
                        "UNSCORABLE"
                        if answer.get("human_decision") is None
                        else "CORRECT" if answer.get("human_decision") else "INCORRECT"
                    ),
                    "confidence": answer.get("confidence", "NOT_RECORDED"),
                    "reason_category": answer.get("disagreement_category", "not-recorded"),
                    "brief_rationale": answer.get("human_rationale", answer.get("disagreement_category", "")),
                    "is_abstention": bool(case.get("is_abstention")),
                    "question_type": case.get("question_type"),
                }
            )
    if len(rows) != 20:
        raise ValueError(f"expected 20 human-audit answers, found {len(rows)}")
    return rows


def choose_provider() -> tuple[str, str]:
    force_local = os.getenv("PSE_FORCE_LOCAL_JUDGE") == "1"
    if os.getenv("OPENAI_API_KEY") and not force_local:
        return "official-openai", "OPENAI_API_KEY present; official LongMemEval model selected before inference"
    return "local-fallback", "No confirmed usable OpenAI API credential; fixed local 3B fallback selected before inference"


def judge_rows(
    judge: Any,
    rows: list[dict[str, Any]],
    raw_output_directory: Path,
) -> list[dict[str, Any]]:
    judgments: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        request_id = f"evaluator-v2:{row['blinded_response_id']}:{uuid.uuid4()}"
        try:
            raw = judge.judge(request_id, row["prompt"])
            raw_text = raw.get("text", "")
            parsed = parse_strict_yes_no(raw_text)
            error = None
        except Exception as exc:
            raw = {"request_id": request_id, "error": str(exc)}
            parsed = parse_strict_yes_no("")
            error = str(exc)
        raw_record = {
            "schema_version": "longmemeval-raw-judge-output-v2",
            "blinded_response_id": row["blinded_response_id"],
            "request_id": request_id,
            "provider": row["provider"],
            "raw_response": raw,
            "error": error,
        }
        json_dump(raw_output_directory / f"{row['blinded_response_id']}.json", raw_record)
        judgments.append(
            {
                "schema_version": "longmemeval-parsed-judgment-v2",
                "blinded_response_id": row["blinded_response_id"],
                "case_id": row.get("case_id"),
                "baseline_id": row.get("baseline_id"),
                "unit_case_id": row.get("unit_case_id"),
                "question_type": row["question_type"],
                "is_abstention": row["is_abstention"],
                "status": parsed.status,
                "correct": parsed.correct,
                "normalized_text": parsed.normalized_text,
                "parser_error": parsed.error,
                "raw_output_file": f"raw-judge-outputs/{row['blinded_response_id']}.json",
                "sequence_index": index,
            }
        )
    return judgments


def build_registry(output_root: Path) -> dict[str, Any]:
    paths = sorted(
        path for path in output_root.rglob("*")
        if path.is_file() and path.name != "artifact-registry.json"
    )
    return {
        "schema_version": "longmemeval-evaluator-artifact-registry-v2",
        "artifact_count": len(paths),
        "artifacts": [
            {
                "path": path.relative_to(output_root).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in paths
        ],
    }


def write_environment_blocked(
    output_root: Path,
    spec: dict[str, Any],
    provider: str,
    selection_reason: str,
    error: str,
    archive_verification: dict[str, Any],
) -> None:
    json_dump(
        output_root / "environment-blocker.json",
        {
            "schema_version": "longmemeval-evaluator-environment-blocker-v2",
            "provider": provider,
            "selection_reason": selection_reason,
            "error": error,
            "completed_work": [
                "official evaluator source and requirements pinned",
                "existing 40-trial archive verified",
                "fixed evaluator specification loaded",
                "blinding and parser implementation available",
            ],
            "unavailable_results": [
                "new judge outputs",
                "evaluator calibration",
                "formal correctness rescoring",
            ],
            "archive_verification": archive_verification,
        },
    )
    verdict = {
        "schema_version": "longmemeval-evaluator-research-verdict-v2",
        "research_verdict": "BLOCKED BY ENVIRONMENT",
        "formal_correctness_use": "PROHIBITED",
        "completion_previous": 24,
        "completion_current": 24,
        "remaining_distance": 76,
        "evidence_cap": 45,
        "reason": error,
        "sealed_final_accessed": False,
        "answer_model_rerun": False,
        "case_ids_changed": False,
        "old_failed_evaluator_preserved": True,
    }
    json_dump(output_root / "research-verdict.json", verdict)
    (output_root / "README.md").write_text(
        "# LongMemEval evaluator v2\n\n"
        "Verdict: **BLOCKED BY ENVIRONMENT**. The existing 40 answer trials remain unchanged and valid, "
        "but the fixed evaluator could not execute in the available environment.\n",
        encoding="utf-8",
    )
    json_dump(output_root / "artifact-registry.json", build_registry(output_root))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--unit-corpus", type=Path, required=True)
    parser.add_argument("--model-server", type=Path, required=True)
    parser.add_argument("--cache-directory", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    output_root = args.output_root
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    archive_verification = verify_archive_registry(args.evidence_root)
    trials = load_trials(args.evidence_root / "raw-trials")
    audit_file = args.evidence_root / "human-audit-completed-blinded.json"
    audit_key_file = args.evidence_root / "human-audit-key.json"
    audit_rows = build_audit_rows(audit_file, audit_key_file)

    # Preserve references to the unchanged v1 evidence and copy audit artifacts without editing them.
    copy_preserving(audit_file, output_root / "human-audit-completed-blinded.json")
    copy_preserving(audit_key_file, output_root / "human-audit-key.json")
    copy_preserving(args.spec, output_root / "evaluator-manifest.json")
    prompt_document = {
        "official_source_repository": OFFICIAL_SOURCE_REPOSITORY,
        "official_source_commit": OFFICIAL_SOURCE_COMMIT,
        "official_source_path": OFFICIAL_SOURCE_PATH,
        "templates": PROMPT_TEMPLATES,
    }
    json_dump(output_root / "prompt-templates.json", prompt_document)
    parser_source = Path(__file__).resolve().parents[1] / "src/personal_state_engine/longmemeval_evaluator.py"
    json_dump(
        output_root / "parser-version.json",
        {
            "schema_version": "longmemeval-parser-version-v2",
            "contract": "exact enum yes/no, case-insensitive, optional terminal period or exclamation mark",
            "source_path": "src/personal_state_engine/longmemeval_evaluator.py",
            "source_sha256": sha256_file(parser_source),
        },
    )
    json_dump(
        output_root / "official-source-audit.json",
        {
            "schema_version": "longmemeval-official-evaluator-source-audit-v1",
            "repository": OFFICIAL_SOURCE_REPOSITORY,
            "commit": OFFICIAL_SOURCE_COMMIT,
            "path": OFFICIAL_SOURCE_PATH,
            "license": "MIT",
            "official_models": ["gpt-4o-2024-08-06", "gpt-4o-mini-2024-07-18", "meta-llama/Meta-Llama-3.1-70B-Instruct"],
            "official_runtime_requirements": {
                "openai": "1.35.1",
                "tqdm": "4.66.4",
                "backoff": "2.2.1",
                "numpy": "1.26.3",
            },
            "local_deviation": {
                "model": LOCAL_FALLBACK_MODEL,
                "revision": LOCAL_FALLBACK_REVISION,
                "reason": "official GPT-4o requires a separate paid API credential; official local 70B path exceeds GitHub-hosted CPU runner resources",
                "prompt_semantics": "official templates preserved",
                "parser": "hardened from substring matching to exact enum validation",
            },
        },
    )

    provider, selection_reason = choose_provider()
    provider_metadata = {
        "provider": provider,
        "selection_reason": selection_reason,
        "selected_before_inference": True,
        "openai_key_present": bool(os.getenv("OPENAI_API_KEY")),
        "force_local": os.getenv("PSE_FORCE_LOCAL_JUDGE") == "1",
    }
    json_dump(output_root / "provider-selection.json", provider_metadata)

    case_to_trials = {(row["case_id"], row["baseline_id"]): row for row in trials}
    blinded_rows: list[dict[str, Any]] = []
    blinding_key_rows: list[dict[str, Any]] = []
    for case_id in sorted({row["case_id"] for row in trials}):
        mapping = deterministic_case_mapping(case_id, int(spec["seed"]))
        key_entry = {"case_id": case_id, "mapping": {}}
        for label in ("A", "B"):
            baseline_id = mapping[label]
            trial = case_to_trials[(case_id, baseline_id)]
            response_id = blinded_response_id(case_id, label, int(spec["seed"]))
            key_entry["mapping"][response_id] = baseline_id
            prompt = build_official_prompt(
                trial["question_type"],
                trial["raw_prompt_or_reconstruction_fields"]["question"],
                trial["reference_answer"],
                trial["parsed_answer"],
                abstention=case_id.endswith("_abs"),
            )
            forbidden = ["EXT-B0", "EXT-B5", "no-memory", "retrieval", "baseline", "control", "treatment"]
            lowered = prompt.lower()
            if any(term.lower() in lowered for term in forbidden):
                raise ValueError(f"baseline identity term leaked into judge prompt for {response_id}")
            blinded_rows.append(
                {
                    "schema_version": "longmemeval-blinded-input-v2",
                    "blinded_response_id": response_id,
                    "case_id": case_id,
                    "baseline_id": baseline_id,  # removed from persisted blinded input below
                    "question_type": trial["question_type"],
                    "is_abstention": case_id.endswith("_abs"),
                    "question": trial["raw_prompt_or_reconstruction_fields"]["question"],
                    "reference_answer": trial["reference_answer"],
                    "candidate_answer": trial["parsed_answer"],
                    "prompt": prompt,
                    "provider": provider,
                }
            )
        blinding_key_rows.append(key_entry)

    persisted_blinded = [
        {key: value for key, value in row.items() if key != "baseline_id"}
        for row in blinded_rows
    ]
    jsonl_dump(output_root / "blinded-inputs.jsonl", persisted_blinded)
    json_dump(
        output_root / "blinding-key.json",
        {
            "schema_version": "longmemeval-blinding-key-v2",
            "seed": spec["seed"],
            "warning": "Open only after judge outputs and human decisions are fixed.",
            "rows": blinding_key_rows,
        },
    )

    unit_cases = json.loads(args.unit_corpus.read_text(encoding="utf-8"))
    unit_rows: list[dict[str, Any]] = []
    for item in unit_cases:
        unit_rows.append(
            {
                "schema_version": "longmemeval-unit-input-v2",
                "blinded_response_id": f"unit-{item['case_id']}",
                "unit_case_id": item["case_id"],
                "question_type": item["question_type"],
                "is_abstention": bool(item["is_abstention"]),
                "prompt": build_official_prompt(
                    item["question_type"], item["question"], item["reference_answer"], item["candidate_answer"],
                    abstention=bool(item["is_abstention"]),
                ),
                "provider": provider,
                "expected_correct": bool(item["expected_correct"]),
            }
        )

    try:
        judge_context = OpenAIJudge() if provider == "official-openai" else LocalNodeJudge(args.model_server, args.cache_directory)
        with judge_context as judge:
            json_dump(output_root / "judge-ready.json", judge.ready)
            unit_judgments = judge_rows(judge, unit_rows, output_root / "raw-judge-outputs" / "unit")
            formal_judgments = judge_rows(judge, blinded_rows, output_root / "raw-judge-outputs" / "formal")
    except Exception as exc:
        write_environment_blocked(output_root, spec, provider, selection_reason, str(exc), archive_verification)
        print(json.dumps({"status": "BLOCKED_BY_ENVIRONMENT", "error": str(exc)}))
        return 0

    # Move raw output paths to actual nested paths.
    for row in unit_judgments:
        row["raw_output_file"] = f"raw-judge-outputs/unit/{row['blinded_response_id']}.json"
    for row in formal_judgments:
        row["raw_output_file"] = f"raw-judge-outputs/formal/{row['blinded_response_id']}.json"
    jsonl_dump(output_root / "parsed-judgments" / "unit.jsonl", unit_judgments)
    jsonl_dump(output_root / "parsed-judgments" / "formal.jsonl", formal_judgments)

    unit_expected = {row["case_id"]: bool(row["expected_correct"]) for row in unit_cases}
    unit_valid = [row for row in unit_judgments if row["status"] == "VALID"]
    unit_correct = sum(row["correct"] == unit_expected[row["unit_case_id"]] for row in unit_valid)
    unit_summary = {
        "schema_version": "longmemeval-evaluator-unit-summary-v2",
        "cases": len(unit_judgments),
        "valid_outputs": len(unit_valid),
        "invalid_outputs": len(unit_judgments) - len(unit_valid),
        "accuracy_on_valid_outputs": unit_correct / len(unit_valid) if unit_valid else None,
        "rows": [
            {**row, "expected_correct": unit_expected[row["unit_case_id"]]}
            for row in unit_judgments
        ],
        "use": "development-only corpus separate from the fixed formal 40 answers",
    }
    json_dump(output_root / "unit-corpus-summary.json", unit_summary)

    judgment_by_key = {(row["case_id"], row["baseline_id"]): row for row in formal_judgments}
    thresholds = spec["calibration_thresholds"]
    calibration = calculate_calibration(
        audit_rows,
        judgment_by_key,
        full_output_count=len(formal_judgments),
        full_invalid_count=sum(row["status"] != "VALID" for row in formal_judgments),
        thresholds=thresholds,
        blinding_verified=True,
        old_evidence_preserved=(args.evidence_root / "evaluator-calibration.json").is_file(),
        raw_outputs_preserved=len(list((output_root / "raw-judge-outputs" / "formal").glob("*.json"))) == 40,
    )
    calibration["evaluator_id"] = spec["evaluator_id"]
    calibration["provider"] = provider
    calibration["prompt_sha256"] = prompt_templates_sha256()
    calibration["parser_sha256"] = sha256_file(parser_source)
    json_dump(output_root / "evaluator-calibration.json", calibration)

    if calibration["calibration_verdict"] == "PASS":
        formal_summary = summarize_formal_results(trials, formal_judgments)
        jsonl_dump(output_root / "formal-rescoring.jsonl", formal_judgments)
        json_dump(output_root / "formal-summary.json", formal_summary)
        json_dump(output_root / "paired-analysis.json", formal_summary["paired"])
        b0 = formal_summary["by_baseline"]["EXT-B0"]["correct"]
        b5 = formal_summary["by_baseline"]["EXT-B5"]["correct"]
        p_value = formal_summary["paired"]["exact_mcnemar_two_sided_p"]
        if b5 > b0 and p_value is not None and p_value < 0.05:
            research_verdict = "SUPPORTED FOR DEVELOPMENT FOLLOW-UP"
        elif b5 < b0:
            research_verdict = "NOT SUPPORTED UNDER CURRENT CONFIGURATION"
        else:
            research_verdict = "INCONCLUSIVE"
        completion = 30
        formal_use = "PERMITTED"
    else:
        formal_summary = None
        json_dump(
            output_root / "formal-rescoring-prohibited.json",
            {
                "schema_version": "formal-rescoring-prohibited-v2",
                "formal_results": "PROHIBITED",
                "reason": "evaluator calibration failed one or more fixed thresholds",
            },
        )
        research_verdict = "BLOCKED"
        completion = 24
        formal_use = "PROHIBITED"

    research_verdict_document = {
        "schema_version": "longmemeval-evaluator-research-verdict-v2",
        "research_verdict": research_verdict,
        "formal_correctness_use": formal_use,
        "calibration_verdict": calibration["calibration_verdict"],
        "provider": provider,
        "completion_previous": 24,
        "completion_current": completion,
        "remaining_distance": 100 - completion,
        "evidence_cap": 45,
        "sealed_final_accessed": False,
        "answer_model_rerun": False,
        "case_ids_changed": False,
        "old_failed_evaluator_preserved": True,
    }
    json_dump(output_root / "research-verdict.json", research_verdict_document)
    json_dump(
        output_root / "environment-manifest.json",
        {
            "schema_version": "longmemeval-evaluator-environment-v2",
            "provider": provider,
            "selection_reason": selection_reason,
            "judge_ready": json.loads((output_root / "judge-ready.json").read_text(encoding="utf-8")),
            "official_source_commit": OFFICIAL_SOURCE_COMMIT,
            "prompt_sha256": prompt_templates_sha256(),
            "parser_sha256": sha256_file(parser_source),
            "archive_verification": archive_verification,
            "python": sys.version,
        },
    )
    readme = [
        "# LongMemEval evaluator v2",
        "",
        f"Provider: `{provider}`",
        f"Calibration: **{calibration['calibration_verdict']}**",
        f"Research verdict: **{research_verdict}**",
        f"Formal correctness use: **{formal_use}**",
        "",
        "The existing 40 EXT-B0/EXT-B5 answers were not regenerated. The 20-case frozen subset and old failed v1 evaluator evidence remain unchanged.",
    ]
    (output_root / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    json_dump(output_root / "artifact-registry.json", build_registry(output_root))

    print(
        json.dumps(
            {
                "status": "COMPLETE",
                "provider": provider,
                "calibration": calibration["calibration_verdict"],
                "research_verdict": research_verdict,
                "formal_correctness_use": formal_use,
                "output_root": str(output_root),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
