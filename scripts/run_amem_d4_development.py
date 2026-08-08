#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

EXPECTED_DATASET_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
EXPECTED_CASE_IDS_SHA256 = "519b4db13813b60ad6a49cce919543b0639524a98bd1b0d1615c53e62cf8cc7e"
EXPECTED_AMEM_COMMIT = "0c8039f28fdcc08189a23c07a3437d9d2482f9c2"
EXPECTED_ANSWER_MODEL = "onnx-community/Qwen2.5-0.5B-Instruct"
EXPECTED_ANSWER_REVISION = "956050e4c6ce7c647091e15311218f80d662559f"
EXPECTED_JUDGE_MODEL = "onnx-community/Llama-3.2-3B-Instruct-ONNX"
EXPECTED_JUDGE_REVISION = "cab364e7d0e1de7aa09e3abc932be92361c5b55f"


def load_module(filename: str, name: str) -> Any:
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


def wilson(successes: int, trials: int, z: float = 1.959963984540054) -> list[float] | None:
    if trials <= 0:
        return None
    p = successes / trials
    denom = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * trials)) / trials) / denom
    return [max(0.0, center - half), min(1.0, center + half)]


def main() -> int:
    from personal_state_engine.external_trials import _render_sessions
    from personal_state_engine.longmemeval import load_longmemeval
    from personal_state_engine.longmemeval_evaluator import build_official_prompt, parse_strict_yes_no
    from personal_state_engine.model_adapters import ModelRequest, RunManifest

    parser = argparse.ArgumentParser(description="Run frozen A-MEM Gate D4 development answer generation and formal evaluator-v2 scoring.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--retrieval-predictions", type=Path, required=True)
    parser.add_argument("--model-manifest", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--model-server", type=Path, required=True)
    parser.add_argument("--cache-directory", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    protocol = load_json(args.protocol)
    source = load_json(args.source_manifest)
    split = load_json(args.split_manifest)
    retrieval = load_json(args.retrieval_predictions)
    model = load_json(args.model_manifest)
    answer_manifest = RunManifest.from_json(args.run_manifest)

    if protocol.get("schema_version") != "amem-d4-development-protocol-v2":
        raise RuntimeError("D4 protocol is not the frozen v2 contract")
    if protocol.get("sealed_final_accessed") is not False or protocol.get("paid_api_allowed") is not False:
        raise RuntimeError("D4 integrity/cost boundary is invalid")
    if protocol["source"]["commit"] != EXPECTED_AMEM_COMMIT:
        raise RuntimeError("D4 A-MEM source commit mismatch")
    if int(protocol["answer_model"]["retrieval_item_limit"]) != 3:
        raise RuntimeError("D4 answer context must use top 3 A-MEM retrievals")
    if int(protocol["answer_model"]["retrieval_token_budget"]) != 1024 or int(protocol["answer_model"]["memory_token_budget"]) != 1024:
        raise RuntimeError("D4 memory budgets must match the frozen development matrix")

    dataset_sha = sha256_file(args.dataset)
    if dataset_sha != EXPECTED_DATASET_SHA256 or dataset_sha != source["expected_sha256"]:
        raise RuntimeError("dataset SHA-256 mismatch")
    if args.dataset.stat().st_size != int(source["expected_size_bytes"]):
        raise RuntimeError("dataset size mismatch")
    if split.get("source_split") != "development" or split.get("sealed_final_accessed") is not False:
        raise RuntimeError("split is not development-only")
    if split.get("case_ids_sha256") != EXPECTED_CASE_IDS_SHA256 or split.get("sample_count") != 20:
        raise RuntimeError("frozen development case identity mismatch")
    without_self = dict(split)
    expected_self = without_self.pop("manifest_sha256", None)
    if expected_self != canonical_sha256(without_self):
        raise RuntimeError("split self hash mismatch")

    if retrieval.get("source_commit") != EXPECTED_AMEM_COMMIT:
        raise RuntimeError("retrieval evidence source commit mismatch")
    if retrieval.get("dataset_sha256") != EXPECTED_DATASET_SHA256:
        raise RuntimeError("retrieval evidence dataset mismatch")
    if retrieval.get("case_ids_sha256") != EXPECTED_CASE_IDS_SHA256 or retrieval.get("case_count") != 20:
        raise RuntimeError("retrieval evidence case freeze mismatch")
    if retrieval.get("sealed_final_accessed") is not False:
        raise RuntimeError("retrieval evidence sealed-final flag is not false")
    prediction_rows = retrieval.get("predictions", [])
    if len(prediction_rows) != 20 or len({row["case_id"] for row in prediction_rows}) != 20:
        raise RuntimeError("retrieval evidence must contain exactly 20 unique cases")
    prediction_by_id = {row["case_id"]: row for row in prediction_rows}
    if set(prediction_by_id) != set(split["case_ids"]):
        raise RuntimeError("retrieval evidence contains missing or extra cases")

    if model.get("model_id") != EXPECTED_ANSWER_MODEL or model.get("model_revision") != EXPECTED_ANSWER_REVISION:
        raise RuntimeError("answer model identity mismatch")
    if answer_manifest.model_id != EXPECTED_ANSWER_MODEL or answer_manifest.model_version != EXPECTED_ANSWER_REVISION:
        raise RuntimeError("answer run manifest identity mismatch")
    if protocol["formal_evaluator"]["judge_model"] != EXPECTED_JUDGE_MODEL or protocol["formal_evaluator"]["judge_revision"] != EXPECTED_JUDGE_REVISION:
        raise RuntimeError("formal evaluator identity mismatch")
    if protocol["formal_evaluator"]["existing_calibration"]["formal_development_correctness_use"] != "PERMITTED":
        raise RuntimeError("formal evaluator is not authorized for development correctness")

    smoke = load_module("run_longmemeval_e3_smoke.py", "d4_e3_support")
    all_examples = load_longmemeval(args.dataset)
    development = smoke.build_grouped_stratified_splits(all_examples, "longmemeval-e3-v1")["development"]
    development_by_id = {example.question_id: example for example in development}
    examples = []
    rows_by_id = {row["case_id"]: row for row in split["records"]}
    for case_id in split["case_ids"]:
        example = development_by_id.get(case_id)
        if example is None:
            raise RuntimeError(f"frozen case missing from pinned development split: {case_id}")
        row = rows_by_id[case_id]
        if row["history_fingerprint"] != smoke.history_fingerprint(example):
            raise RuntimeError(f"history fingerprint mismatch: {case_id}")
        examples.append(example)

    code_commit = os.environ.get("GITHUB_SHA", "UNAVAILABLE")
    run_id = f"amem-d4-{os.environ.get('GITHUB_RUN_ID', int(time.time()))}-attempt-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
    out = args.output_root / run_id
    raw_answer_dir = out / "raw-answers"
    raw_judge_dir = out / "raw-judge-outputs"
    raw_answer_dir.mkdir(parents=True, exist_ok=False)
    raw_judge_dir.mkdir(parents=True, exist_ok=False)

    answer_environment = os.environ.copy()
    answer_environment.update({
        "PSE_MODEL_ID": EXPECTED_ANSWER_MODEL,
        "PSE_MODEL_REVISION": EXPECTED_ANSWER_REVISION,
        "PSE_MODEL_DTYPE": model["quantization"],
        "PSE_HF_CACHE": args.cache_directory.as_posix(),
    })

    answer_rows: list[dict[str, Any]] = []
    for index, example in enumerate(examples, start=1):
        prediction = prediction_by_id[example.question_id]
        session_by_id = {str(session.session_id): session for session in example.sessions}
        ranked_ids = [str(item) for item in prediction["retrieved_session_ids"]]
        if len(ranked_ids) < 3:
            raise RuntimeError(f"case {example.question_id} has fewer than 3 A-MEM retrievals")
        selected_ids = ranked_ids[:3]
        if len(set(selected_ids)) != len(selected_ids):
            raise RuntimeError(f"case {example.question_id} has duplicate top-3 retrievals")
        missing = [item for item in selected_ids if item not in session_by_id]
        if missing:
            raise RuntimeError(f"case {example.question_id} contains unmapped retrieved sessions: {missing}")
        selected = tuple(session_by_id[item] for item in selected_ids)
        history, context_ids, history_tokens, truncated = _render_sessions(selected, token_budget=1024)
        system_prompt = (
            "Answer the user's question using only the supplied conversation history. "
            "If the history is insufficient, say that the answer is unknown. "
            "Return only the answer, without explaining the retrieval method."
        )
        user_content = f"Question date: {example.question_date}\nQuestion: {example.question}"
        if history:
            user_content = f"Conversation history:\n{history}\n\n{user_content}"
        request_id = f"{run_id}:{example.question_id}:{uuid.uuid4()}"
        request = ModelRequest(
            request_id=request_id,
            system_prompt=system_prompt,
            messages=({"role": "user", "content": user_content},),
            manifest=answer_manifest,
        )
        adapter = smoke.PersistentNodeAdapter(["node", args.model_server.as_posix()], answer_environment)
        try:
            started = time.time()
            response = adapter.complete(request)
            elapsed_ms = max(0.0, (time.time() - started) * 1000)
        finally:
            adapter.close()
        if not response.text or not response.text.strip():
            raise RuntimeError(f"case {example.question_id} produced a blank answer")
        usage = dict(response.usage or {})
        answer_row = {
            "schema_version": "amem-d4-answer-trial-v1",
            "run_id": run_id,
            "case_id": example.question_id,
            "question_type": example.question_type,
            "is_abstention": bool(example.is_abstention),
            "question": example.question,
            "question_date": example.question_date,
            "reference_answer": example.answer,
            "amem_retrieval_run_id": retrieval.get("run_id"),
            "amem_source_commit": EXPECTED_AMEM_COMMIT,
            "ranked_retrieved_session_ids": ranked_ids,
            "answer_context_top_k": 3,
            "selected_session_ids_before_budget": selected_ids,
            "context_session_ids": list(context_ids),
            "history_lexical_tokens": history_tokens,
            "history_token_budget": 1024,
            "history_truncated": truncated,
            "prompt_template_version": "longmemeval-answer-v1",
            "request_id": request_id,
            "answer_model": EXPECTED_ANSWER_MODEL,
            "answer_model_revision": EXPECTED_ANSWER_REVISION,
            "parsed_answer": response.text,
            "raw_model_output": response.raw,
            "input_tokens": int(usage.get("input_tokens", 0) or 0),
            "output_tokens": int(usage.get("output_tokens", 0) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
            "model_latency_ms": float(response.latency_ms if response.latency_ms is not None else elapsed_ms),
            "new_monetary_cost_usd": 0.0,
            "sealed_final_accessed": False,
            "sequence_index": index,
        }
        write_json(raw_answer_dir / f"{example.question_id}.json", answer_row)
        answer_rows.append(answer_row)
        print(json.dumps({"event": "d4_answer_complete", "case_id": example.question_id, "index": index}, sort_keys=True), flush=True)

    evaluator_module = load_module("run_longmemeval_evaluator_v2.py", "d4_evaluator_v2")
    judged_rows: list[dict[str, Any]] = []
    with evaluator_module.LocalNodeJudge(args.model_server, args.cache_directory, dtype="q4") as judge:
        ready = dict(judge.ready or {})
        if ready.get("model_id") not in {EXPECTED_JUDGE_MODEL, None}:
            raise RuntimeError(f"judge ready model mismatch: {ready.get('model_id')}")
        write_json(out / "judge-ready.json", ready)
        for index, answer in enumerate(answer_rows, start=1):
            prompt = build_official_prompt(
                answer["question_type"],
                answer["question"],
                answer["reference_answer"],
                answer["parsed_answer"],
                abstention=bool(answer["is_abstention"]),
            )
            forbidden = ["A-MEM", "EXT-B0", "EXT-B5", "baseline", "retrieval method"]
            if any(term.lower() in prompt.lower() for term in forbidden):
                raise RuntimeError(f"baseline identity leaked into judge prompt for {answer['case_id']}")
            judge_request_id = f"amem-d4-eval:{answer['case_id']}:{uuid.uuid4()}"
            raw = judge.judge(judge_request_id, prompt)
            parsed = parse_strict_yes_no(str(raw.get("text", "")))
            raw_payload = {
                "schema_version": "amem-d4-raw-judge-output-v1",
                "case_id": answer["case_id"],
                "request_id": judge_request_id,
                "evaluator_id": protocol["formal_evaluator"]["evaluator_id"],
                "judge_model": EXPECTED_JUDGE_MODEL,
                "judge_revision": EXPECTED_JUDGE_REVISION,
                "baseline_identity_hidden": True,
                "raw_response": raw,
                "sealed_final_accessed": False,
            }
            write_json(raw_judge_dir / f"{answer['case_id']}.json", raw_payload)
            judged = {
                "case_id": answer["case_id"],
                "question_type": answer["question_type"],
                "is_abstention": answer["is_abstention"],
                "status": parsed.status,
                "correct": parsed.correct,
                "normalized_text": parsed.normalized_text,
                "parser_error": parsed.error,
                "sequence_index": index,
            }
            judged_rows.append(judged)
            print(json.dumps({"event": "d4_judge_complete", "case_id": answer["case_id"], "status": parsed.status}, sort_keys=True), flush=True)

    if len(judged_rows) != 20 or any(row["status"] != "VALID" for row in judged_rows):
        raise RuntimeError("D4 formal scoring failed: all 20 judge outputs must be valid")
    correct = sum(bool(row["correct"]) for row in judged_rows)
    abstention_rows = [row for row in judged_rows if row["is_abstention"]]
    abstention_correct = sum(bool(row["correct"]) for row in abstention_rows)
    latencies = [float(row["model_latency_ms"]) for row in answer_rows]
    total_input = sum(int(row["input_tokens"]) for row in answer_rows)
    total_output = sum(int(row["output_tokens"]) for row in answer_rows)

    write_json(out / "formal-judgments.json", {
        "schema_version": "amem-d4-formal-judgments-v1",
        "evaluator_id": protocol["formal_evaluator"]["evaluator_id"],
        "judge_model": EXPECTED_JUDGE_MODEL,
        "judge_revision": EXPECTED_JUDGE_REVISION,
        "baseline_identity_hidden": True,
        "invalid_output_count": 0,
        "rows": judged_rows,
    })
    summary = {
        "schema_version": "amem-d4-development-summary-v1",
        "run_id": run_id,
        "source_commit": EXPECTED_AMEM_COMMIT,
        "retrieval_run_id": retrieval.get("run_id"),
        "case_count": 20,
        "abstention_case_count": len(abstention_rows),
        "completed_answer_trials": len(answer_rows),
        "correct": correct,
        "answer_accuracy": correct / 20,
        "wilson_95_ci": wilson(correct, 20),
        "abstention_correct": abstention_correct,
        "abstention_accuracy": abstention_correct / len(abstention_rows) if abstention_rows else None,
        "judge_invalid_count": 0,
        "judge_invalid_rate": 0.0,
        "answer_input_tokens": total_input,
        "answer_output_tokens": total_output,
        "answer_total_tokens": total_input + total_output,
        "median_answer_latency_ms": statistics.median(latencies),
        "max_answer_latency_ms": max(latencies),
        "answer_model": EXPECTED_ANSWER_MODEL,
        "answer_model_revision": EXPECTED_ANSWER_REVISION,
        "evaluator_id": protocol["formal_evaluator"]["evaluator_id"],
        "judge_model": EXPECTED_JUDGE_MODEL,
        "judge_revision": EXPECTED_JUDGE_REVISION,
        "protocol_sha256": sha256_file(args.protocol),
        "retrieval_predictions_sha256": sha256_file(args.retrieval_predictions),
        "split_manifest_sha256": sha256_file(args.split_manifest),
        "dataset_sha256": dataset_sha,
        "new_monetary_cost_usd": 0.0,
        "paid_api_used": False,
        "cloud_gpu_used": False,
        "sealed_final_accessed": False,
        "claim_limit": "Gate D4 development evidence only; no parity, superiority, equivalence, non-inferiority, SOTA, sealed-final, or independent-reproduction claim.",
    }
    write_json(out / "summary.json", summary)
    environment = {
        "schema_version": "amem-d4-environment-v1",
        "platform": platform.platform(),
        "python": sys.version,
        "node": subprocess.run(["node", "--version"], capture_output=True, text=True, check=True).stdout.strip(),
        "cpu_count": os.cpu_count(),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "github_sha": code_commit,
        "new_monetary_cost_usd": 0.0,
        "sealed_final_accessed": False,
    }
    write_json(out / "environment.json", environment)

    artifacts = []
    for path in sorted(p for p in out.rglob("*") if p.is_file() and p.name != "artifact-registry.json"):
        artifacts.append({
            "path": path.relative_to(out).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "source_commit": code_commit,
            "source_workflow_run": os.environ.get("GITHUB_RUN_ID"),
            "generation_command": "python scripts/run_amem_d4_development.py ...",
        })
    registry = {
        "schema_version": "amem-d4-artifact-registry-v1",
        "run_id": run_id,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "source_amem_commit": EXPECTED_AMEM_COMMIT,
        "source_retrieval_run": retrieval.get("run_id"),
        "protocol_sha256": sha256_file(args.protocol),
        "dataset_sha256": dataset_sha,
        "case_ids_sha256": EXPECTED_CASE_IDS_SHA256,
        "new_monetary_cost_usd": 0.0,
        "sealed_final_accessed": False,
    }
    write_json(out / "artifact-registry.json", registry)
    print(json.dumps({"status": "AMEM_D4_DEVELOPMENT_COMPLETE", "run_id": run_id, "answer_accuracy": summary["answer_accuracy"], "correct": correct, "cases": 20}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
