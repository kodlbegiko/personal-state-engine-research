#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any


def load_module(filename: str, name: str) -> Any:
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} must contain an object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the fixed development matrix from a verified minimal execution subset.")
    parser.add_argument("source_dataset", type=Path)
    parser.add_argument("execution_subset", type=Path)
    parser.add_argument("--execution-subset-manifest", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--model-manifest", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--matrix-config", type=Path, required=True)
    parser.add_argument("--model-server", type=Path, required=True)
    parser.add_argument("--cache-directory", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    from personal_state_engine.external_trials import ExternalTrialConfig, execute_trial, write_immutable_trial
    from personal_state_engine.longmemeval import load_longmemeval
    from personal_state_engine.model_adapters import RunManifest

    args = parse_args()
    support = load_module("run_longmemeval_development_matrix.py", "development_support")
    smoke = load_module("run_longmemeval_e3_smoke.py", "e3_support")
    source = load_json(args.source_manifest)
    protocol = load_json(args.protocol)
    split = load_json(args.split_manifest)
    subset_manifest = load_json(args.execution_subset_manifest)
    model = load_json(args.model_manifest)
    matrix = load_json(args.matrix_config)
    answer_manifest = RunManifest.from_json(args.run_manifest)

    source_hash = sha256_file(args.source_dataset)
    if source_hash != source["expected_sha256"] or source_hash != protocol["dataset"]["sha256"]:
        raise RuntimeError("source dataset hash mismatch")
    if args.source_dataset.stat().st_size != int(source["expected_size_bytes"]):
        raise RuntimeError("source dataset size mismatch")
    if sha256_file(args.execution_subset) != subset_manifest["execution_subset_sha256"]:
        raise RuntimeError("execution subset hash mismatch")
    if args.execution_subset.stat().st_size != int(subset_manifest["execution_subset_size_bytes"]):
        raise RuntimeError("execution subset size mismatch")
    if subset_manifest["source_dataset_sha256"] != source_hash:
        raise RuntimeError("execution subset source provenance mismatch")
    if subset_manifest["formal_case_ids"] != split["case_ids"]:
        raise RuntimeError("execution subset formal cases differ from frozen split")
    if subset_manifest.get("sealed_final_accessed") is not False:
        raise RuntimeError("sealed-final flag is not false")

    examples = load_longmemeval(args.execution_subset)
    by_id = {example.question_id: example for example in examples}
    formal = [by_id[case_id] for case_id in subset_manifest["formal_case_ids"]]
    screening = [by_id[case_id] for case_id in subset_manifest["screening_case_ids"]]
    if len(formal) != 20 or len(screening) != 2:
        raise RuntimeError("execution subset case counts are invalid")
    for row, example in zip(split["records"], formal, strict=True):
        if row["case_id"] != example.question_id:
            raise RuntimeError("formal case order mismatch")
        if row["question_type"] != example.question_type:
            raise RuntimeError("formal question type mismatch")
        if bool(row["is_abstention"]) != example.is_abstention:
            raise RuntimeError("formal abstention flag mismatch")
        if row["history_fingerprint"] != smoke.history_fingerprint(example):
            raise RuntimeError("formal history fingerprint mismatch")

    model_revision = support.require_exact_revision(model["model_revision"], field="model_revision")
    tokenizer_revision = support.require_exact_revision(model["tokenizer_revision"], field="tokenizer_revision")
    if answer_manifest.model_id != model["model_id"] or answer_manifest.model_version != model_revision:
        raise RuntimeError("model manifests disagree")

    code_commit = os.environ.get("GITHUB_SHA", "UNAVAILABLE")
    source_head_sha = os.environ.get("PSE_SOURCE_HEAD_SHA", code_commit)
    run_id = f"development-matrix-{os.environ.get('GITHUB_RUN_ID', int(time.time()))}-attempt-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
    run_directory = args.output_root / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    environment = os.environ.copy()
    environment.update({
        "PSE_MODEL_ID": model["model_id"],
        "PSE_MODEL_REVISION": model_revision,
        "PSE_MODEL_DTYPE": model["quantization"],
        "PSE_HF_CACHE": args.cache_directory.as_posix(),
    })
    adapter = smoke.PersistentNodeAdapter(["node", args.model_server.as_posix()], environment)
    records = []
    try:
        cache_path = write_json(run_directory / "model-cache-manifest.json", smoke.cache_manifest(args.cache_directory))
        environment_path = write_json(run_directory / "environment-manifest.json", {
            "schema_version": "development-environment-manifest-v2",
            "platform": platform.platform(),
            "python": sys.version,
            "node": subprocess.run(["node", "--version"], capture_output=True, text=True, check=True).stdout.strip(),
            "cpu_count": os.cpu_count(),
            "machine": platform.machine(),
            "tested_commit_sha": code_commit,
            "source_head_sha": source_head_sha,
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "source_dataset_sha256": source_hash,
            "execution_subset_sha256": sha256_file(args.execution_subset),
            "model_cache_manifest_sha256": sha256_file(cache_path),
            "security_scope": model["security_scope"],
        })
        environment_hash = sha256_file(environment_path)
        screening_rows = []
        for example in screening:
            config = ExternalTrialConfig(
                run_id=run_id + "-screen",
                dataset_name=protocol["dataset"]["name"],
                dataset_version=protocol["dataset"]["revision"],
                dataset_sha256=source_hash,
                split_name="development-screening",
                split_manifest_sha256=sha256_file(args.split_manifest),
                baseline_id="EXT-B0",
                baseline_version="external-baseline-v1",
                retrieval_item_limit=int(matrix["retrieval"]["k"]),
                retrieval_token_budget=int(matrix["retrieval"]["retrieval_token_budget"]),
                memory_token_budget=int(matrix["retrieval"]["memory_token_budget"]),
                code_commit=code_commit,
                environment_manifest_sha256=environment_hash,
            )
            record = execute_trial(example, answer_manifest, config, adapter)
            screening_rows.append({
                "case_id": example.question_id,
                "status": record.status,
                "non_blank_output": bool(record.parsed_answer and record.parsed_answer.strip()),
                "latency_ms": record.latency_ms,
                "error_type": record.error_type,
                "error_message": record.error_message,
            })
        screening_pass = all(row["status"] == "completed" and row["non_blank_output"] for row in screening_rows)
        screening_path = write_json(run_directory / "model-capability-screening.json", {
            "schema_version": "model-capability-screening-v1",
            "formal_matrix_overlap": False,
            "sealed_final_accessed": False,
            "selection_rule": subset_manifest["selection_rule"],
            "criteria": "runtime success and non-blank output only",
            "rows": screening_rows,
            "verdict": "PASS" if screening_pass else "FAIL",
            "limitation": "Executability only; not proof that floor effect is absent.",
        })
        if not screening_pass:
            raise RuntimeError("answer model failed screening")

        raw_directory = run_directory / "raw-trials"
        retrieval_k = int(matrix["retrieval"]["k"])
        for example in formal:
            ranked = smoke.bm25_scores(
                example.question,
                example.sessions,
                k=retrieval_k,
                k1=float(matrix["retrieval"]["k1"]),
                b=float(matrix["retrieval"]["b"]),
            )
            score_by_session = {session.session_id: score for session, score in ranked}
            for baseline in protocol["baseline_ids"]:
                config = ExternalTrialConfig(
                    run_id=run_id,
                    dataset_name=protocol["dataset"]["name"],
                    dataset_version=protocol["dataset"]["revision"],
                    dataset_sha256=source_hash,
                    split_name="development",
                    split_manifest_sha256=sha256_file(args.split_manifest),
                    baseline_id=baseline,
                    baseline_version="external-baseline-v1",
                    retrieval_item_limit=retrieval_k,
                    retrieval_token_budget=int(matrix["retrieval"]["retrieval_token_budget"]),
                    memory_token_budget=int(matrix["retrieval"]["memory_token_budget"]),
                    prompt_template_version="longmemeval-answer-v1",
                    evaluator_id=matrix["evaluator"]["id"],
                    evaluator_version="1",
                    code_commit=code_commit,
                    environment_manifest_sha256=environment_hash,
                )
                record = execute_trial(example, answer_manifest, config, adapter)
                deterministic = smoke.provisional_evaluate(record.parsed_answer, example.answer, is_abstention=example.is_abstention)
                semantic = support.semantic_judge(
                    adapter,
                    answer_manifest,
                    case_id=example.question_id,
                    question=example.question,
                    reference=example.answer,
                    candidate=record.parsed_answer,
                    is_abstention=example.is_abstention,
                )
                evaluator_output = {
                    "status": "SEMANTIC_SCORED" if semantic.get("score") is not None else "SEMANTIC_INVALID",
                    "score": semantic.get("score"),
                    "deterministic_diagnostic": deterministic,
                    "semantic": semantic,
                    "calibration_status": "PENDING_HUMAN_AUDIT",
                }
                enriched = replace(
                    record,
                    tokenizer_id=model["tokenizer_id"],
                    tokenizer_revision=tokenizer_revision,
                    runtime_name=model["runtime_name"],
                    runtime_version=model["runtime_version"],
                    quantization=model["quantization"],
                    hardware=model["hardware"],
                    retrieval_scores=tuple(score_by_session.get(item, 0.0) for item in record.retrieved_items),
                    evaluator_id=matrix["evaluator"]["id"],
                    evaluator_version="1",
                    evaluator_output=evaluator_output,
                    estimated_cost=0.0,
                )
                write_immutable_trial(enriched, raw_directory)
                records.append(enriched)
    finally:
        adapter.close()

    summary = support.build_summary(formal, records)
    summary.update({
        "run_id": run_id,
        "source_dataset_sha256": source_hash,
        "execution_subset_sha256": sha256_file(args.execution_subset),
        "execution_subset_manifest_sha256": sha256_file(args.execution_subset_manifest),
        "protocol_sha256": sha256_file(args.protocol),
        "split_manifest_sha256": sha256_file(args.split_manifest),
        "model_manifest_sha256": sha256_file(args.model_manifest),
        "matrix_config_sha256": sha256_file(args.matrix_config),
        "tested_commit_sha": code_commit,
        "source_head_sha": source_head_sha,
        "model_id": model["model_id"],
        "model_revision": model_revision,
        "environment_manifest_sha256": sha256_file(environment_path),
        "model_capability_screening_sha256": sha256_file(screening_path),
        "sealed_final_accessed": False,
    })
    summary_path = write_json(run_directory / "processed-summary.json", summary)
    audit_queue, audit_key = support.build_human_audit_queue(formal, records)
    queue_path = write_json(run_directory / "human-audit-queue.json", audit_queue)
    key_path = write_json(run_directory / "human-audit-key.json", audit_key)

    registry = []
    for path, artifact_type, sources in (
        (cache_path, "model-cache-manifest", (args.model_manifest.as_posix(),)),
        (environment_path, "environment-manifest", (cache_path.as_posix(),)),
        (screening_path, "model-capability-screening", (args.execution_subset_manifest.as_posix(),)),
        (summary_path, "processed-summary", ("raw-trials",)),
        (queue_path, "human-audit-queue", (summary_path.as_posix(),)),
        (key_path, "human-audit-key", (queue_path.as_posix(),)),
    ):
        support.add_registry_entry(
            registry,
            path,
            artifact_type,
            command="python scripts/run_longmemeval_development_subset.py ...",
            code_commit=code_commit,
            dataset_hash=source_hash,
            split_hash=sha256_file(args.split_manifest),
            config_hash=sha256_file(args.matrix_config),
            model_manifest_hash=sha256_file(args.model_manifest),
            source_artifacts=sources,
        )
    for path in sorted((run_directory / "raw-trials").glob("*.json")):
        support.add_registry_entry(
            registry,
            path,
            "raw-trial",
            command="python scripts/run_longmemeval_development_subset.py ...",
            code_commit=code_commit,
            dataset_hash=source_hash,
            split_hash=sha256_file(args.split_manifest),
            config_hash=sha256_file(args.matrix_config),
            model_manifest_hash=sha256_file(args.model_manifest),
            source_artifacts=(args.execution_subset_manifest.as_posix(), args.model_manifest.as_posix()),
        )
    registry_path = write_json(run_directory / "artifact-registry.json", {
        "schema_version": "artifact-registry-v2",
        "run_id": run_id,
        "tested_commit_sha": code_commit,
        "source_head_sha": source_head_sha,
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "artifact_count": len(registry),
        "artifacts": registry,
    })
    print(json.dumps({
        "status": "DEVELOPMENT_MATRIX_COMPLETED",
        "run_id": run_id,
        "cases": len(formal),
        "trials": len(records),
        "completed": sum(record.status == "completed" for record in records),
        "errors": sum(record.status == "error" for record in records),
        "timeouts": sum(record.status == "timeout" for record in records),
        "artifact_registry": registry_path.as_posix(),
    }, sort_keys=True))
    return 0 if len(records) == 40 else 1


if __name__ == "__main__":
    raise SystemExit(main())
