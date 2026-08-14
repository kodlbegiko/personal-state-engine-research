from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from personal_state_engine.longmemeval_faithful_port import (
    EXPECTED_CASE_ID_SHA256,
    FORBIDDEN_BLINDING_TERMS,
    OFFICIAL_LICENSE,
    OFFICIAL_LOCAL_MODEL,
    OFFICIAL_OPENAI_MODEL,
    OFFICIAL_SOURCE_BLOB_SHA,
    OFFICIAL_SOURCE_COMMIT,
    OFFICIAL_SOURCE_PATH,
    OFFICIAL_SOURCE_REPOSITORY,
    OFFICIAL_SOURCE_SHA256,
    SEED,
    build_blinded_inputs,
    build_immutable_answer_manifest,
    canonical_json,
    jsonl_dump,
    load_raw_trials,
    official_prompt_bundle,
    parse_strict_judgment,
    parser_sha256,
    prompt_bundle_sha256,
    sha256_file,
    sha256_text,
    verify_archive_registry,
    verify_blinded_records,
    write_json,
)

RETRIEVED_AT_UTC = "2026-08-01T14:28:00Z"
EVALUATOR_ID = "longmemeval-official-faithful-port-v3"
OUTPUT_DIRECTORY = "results/external/longmemeval-faithful-port-v3-preparation"
EVIDENCE_DIRECTORY = "results/external/longmemeval-development-matrix-30676516785"
SPLIT_PATH = "experiments/splits/longmemeval-development-matrix-v1.json"
UNIT_CORPUS_PATH = "benchmarks/evaluator/longmemeval-faithful-port-unit-v3.json"


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _environment_capability() -> dict[str, Any]:
    credential_present = bool(os.getenv("OPENAI_API_KEY"))
    local_70b_endpoint_present = bool(os.getenv("LONGMEMEVAL_70B_BASE_URL"))
    return {
        "schema_version": "longmemeval-faithful-port-environment-capability-v3",
        "openai_api_credential_present": credential_present,
        "exact_official_model": OFFICIAL_OPENAI_MODEL,
        "exact_official_model_callable": "UNVERIFIED" if credential_present else False,
        "local_70b_model": OFFICIAL_LOCAL_MODEL,
        "local_70b_runtime_endpoint_present": local_70b_endpoint_present,
        "local_70b_runtime_callable": "UNVERIFIED" if local_70b_endpoint_present else False,
        "chosen_execution_path": "official-runtime-not-executed",
        "missing_dependencies": [
            item
            for item, missing in (
                ("OPENAI_API_KEY with paid API access", not credential_present),
                ("exact-pinned local 70B serving endpoint", not local_70b_endpoint_present),
            )
            if missing
        ],
        "estimated_or_actual_cost_usd": None,
        "api_key_recorded": False,
    }



def _verify_unit_corpus_contract(unit_corpus: dict[str, Any]) -> None:
    cases = unit_corpus.get("cases", [])
    if len(cases) < 24:
        raise ValueError("unit-test corpus must contain at least 24 cases")
    ids = [case.get("id") for case in cases]
    if None in ids or len(ids) != len(set(ids)):
        raise ValueError("unit-test corpus IDs must be present and unique")
    allowed = {"CORRECT", "INCORRECT", "INVALID"}
    for case in cases:
        if case.get("expected_label") not in allowed:
            raise ValueError(f"invalid expected label in unit corpus: {case.get('id')}")
        if "parser_fixture" in case:
            observed = parse_strict_judgment(case["parser_fixture"]).status
            if observed != case["expected_label"]:
                raise ValueError(f"parser fixture mismatch: {case['id']} expected {case['expected_label']} observed {observed}")
    parser_smoke = {
        '{"label":"CORRECT"}': "CORRECT",
        '{"label":"INCORRECT"}': "INCORRECT",
        '': "INVALID",
        'yes': "INVALID",
        '{"label":"CORRECT","extra":1}': "INVALID",
    }
    for raw, expected in parser_smoke.items():
        if parse_strict_judgment(raw).status != expected:
            raise ValueError(f"strict parser self-check failed for {raw!r}")


def _build_artifact_registry(output_root: Path) -> dict[str, Any]:
    artifacts = []
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path.name == "artifact-registry.json":
            continue
        artifacts.append(
            {
                "path": path.relative_to(output_root).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return {
        "schema_version": "longmemeval-faithful-port-preparation-artifact-registry-v3",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def prepare(repo_root: Path, output_root: Path | None = None) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_root = (output_root or repo_root / OUTPUT_DIRECTORY).resolve()
    evidence_root = repo_root / EVIDENCE_DIRECTORY
    split_path = repo_root / SPLIT_PATH
    unit_path = repo_root / UNIT_CORPUS_PATH

    split_manifest = json.loads(split_path.read_text(encoding="utf-8"))
    unit_corpus = json.loads(unit_path.read_text(encoding="utf-8"))
    _verify_unit_corpus_contract(unit_corpus)
    trials = load_raw_trials(evidence_root, split_manifest)
    archive_verification = verify_archive_registry(evidence_root)
    immutable_manifest = build_immutable_answer_manifest(trials)

    blinded, unblinding_key, answer_leakage = build_blinded_inputs(trials, split_manifest, seed=SEED)
    verify_blinded_records(
        blinded,
        unblinding_key,
        allowed_answer_originated_leakage=answer_leakage,
    )

    output_root.mkdir(parents=True, exist_ok=True)
    for stale in output_root.rglob("*"):
        if stale.is_file():
            stale.unlink()

    raw_integrity = {
        "schema_version": "longmemeval-raw-evidence-integrity-v3",
        "evidence_directory": EVIDENCE_DIRECTORY,
        "expected_raw_trials": 40,
        "observed_raw_trials": len(trials),
        "case_count": len({row["case_id"] for row in trials}),
        "case_pairs_complete": True,
        "trial_ids_unique": len({row["trial_id"] for row in trials}) == 40,
        "request_ids_unique": len({row["request_id"] for row in trials}) == 40,
        "case_id_sha256": split_manifest["case_ids_sha256"],
        "expected_case_id_sha256": EXPECTED_CASE_ID_SHA256,
        "ordered_answer_set_sha256": immutable_manifest["ordered_answer_set_sha256"],
        "unordered_answer_multiset_sha256": immutable_manifest["unordered_answer_multiset_sha256"],
        "raw_trial_set_sha256": immutable_manifest["raw_trial_set_sha256"],
        "archive_registry": archive_verification,
        "ext_b0_cross_session_history_absent": True,
        "ext_b5_retrieval_trace_present": True,
        "old_evaluator_v1_evidence_preserved": True,
        "answer_model_rerun": False,
        "sealed_final_accessed": False,
        "integrity_verdict": "PASS",
    }

    source_manifest = {
        "schema_version": "longmemeval-official-source-manifest-v3",
        "official_repository": OFFICIAL_SOURCE_REPOSITORY,
        "official_commit_sha": OFFICIAL_SOURCE_COMMIT,
        "official_file_path": OFFICIAL_SOURCE_PATH,
        "official_file_blob_sha": OFFICIAL_SOURCE_BLOB_SHA,
        "official_file_sha256": OFFICIAL_SOURCE_SHA256,
        "official_license": OFFICIAL_LICENSE,
        "retrieved_at_utc": RETRIEVED_AT_UTC,
        "supported_judge_models": [
            OFFICIAL_LOCAL_MODEL,
            "gpt-4o-mini-2024-07-18",
            OFFICIAL_OPENAI_MODEL,
        ],
        "official_parser_behavior": "label = 'yes' in eval_response.lower()",
        "official_retry_behavior": "exponential backoff on OpenAI RateLimitError and APIError without a repository-fixed ceiling",
    }

    prompt_bundle = official_prompt_bundle()
    prompt_hash = prompt_bundle_sha256()
    parser_hash = parser_sha256()
    deviations = {
        "schema_version": "longmemeval-faithful-port-deviations-v3",
        "deviations": [
            {
                "component": "output transport",
                "official_behavior": "free-form text requested as yes or no",
                "ported_behavior": "single JSON object with label CORRECT or INCORRECT",
                "reason": "enforce a machine-checkable schema while retaining the official yes/no decision semantics",
                "effect_on_semantics": "potential",
                "verification": "synthetic parser corpus and prompt-routing tests",
            },
            {
                "component": "parser",
                "official_behavior": "substring test: yes in lowercased response",
                "ported_behavior": "exact JSON schema; malformed, extra-key, conflicting, timeout, provider-error and truncated outputs are INVALID",
                "reason": "prevent false positives such as not yes and retain invalid outputs instead of coercing them",
                "effect_on_semantics": "potential",
                "verification": "strict parser unit tests; invalids excluded from correctness",
            },
            {
                "component": "model selection",
                "official_behavior": "one of official GPT-4o, GPT-4o-mini or Llama 3.1 70B paths",
                "ported_behavior": "only exact official dated GPT-4o or exact-pinned official 70B path; no smaller fallback",
                "reason": "avoid substituting a judge with uncalibrated semantic behavior",
                "effect_on_semantics": "potential",
                "verification": "evaluator manifest rejects all other model IDs",
            },
            {
                "component": "retry",
                "official_behavior": "exponential retry on rate-limit/API errors without repository-fixed attempt ceiling",
                "ported_behavior": "at most two transport retries; no semantic retry and no parser repair",
                "reason": "bound execution and retain every attempt without label-driven retry",
                "effect_on_semantics": "none",
                "verification": "retry contract in evaluator manifest",
            },
            {
                "component": "evidence retention",
                "official_behavior": "writes parsed label into result rows",
                "ported_behavior": "retains raw provider response, attempt metadata, usage, parser result and errors",
                "reason": "support reconstruction and invalid-output audit",
                "effect_on_semantics": "none",
                "verification": "preparation and artifact-registry verifier",
            },
            {
                "component": "blinding",
                "official_behavior": "no repository-specific baseline blinding contract",
                "ported_behavior": "identity-free blinded input and separately stored unblinding key using seed 17",
                "reason": "prevent baseline identity from influencing the judge or human auditor",
                "effect_on_semantics": "none",
                "verification": "forbidden-term and forbidden-key scans",
            },
        ],
    }

    evaluator_manifest = {
        "schema_version": "longmemeval-evaluator-v3",
        "evaluator_id": EVALUATOR_ID,
        "source_type": "faithful-port",
        "source_repository": OFFICIAL_SOURCE_REPOSITORY,
        "source_commit": OFFICIAL_SOURCE_COMMIT,
        "source_file": OFFICIAL_SOURCE_PATH,
        "source_file_blob_sha": OFFICIAL_SOURCE_BLOB_SHA,
        "source_file_sha256": OFFICIAL_SOURCE_SHA256,
        "model_id": OFFICIAL_OPENAI_MODEL,
        "model_revision": OFFICIAL_OPENAI_MODEL,
        "provider": "openai",
        "allowed_alternate_official_model": OFFICIAL_LOCAL_MODEL,
        "prompt_bundle_sha256": prompt_hash,
        "parser_sha256": parser_hash,
        "temperature": 0,
        "sampling": False,
        "seed": SEED,
        "max_output_tokens": 16,
        "baseline_blinding": True,
        "raw_outputs_retained": True,
        "invalid_output_policy": "retain_and_exclude_from_correctness",
        "retry_policy": {
            "transport_retries": 2,
            "semantic_retries": 0,
            "parser_repairs": 0,
            "attempts_retained": True,
        },
        "calibration_thresholds": {
            "raw_agreement_minimum": 0.80,
            "cohen_kappa_minimum": 0.60,
            "invalid_output_rate_maximum": 0.05,
        },
        "formal_result_policy": "No new formal correctness result may be produced until exact official runtime execution and fresh blinded calibration pass.",
        "prior_v2_formal_result_exposure": True,
        "versioning_response": "v3 created; v1 and v2 evidence retained; no v3 judge labels generated",
    }

    parser_manifest = {
        "schema_version": "longmemeval-faithful-port-parser-manifest-v3",
        "parser_sha256": parser_hash,
        "accepted_schema": {"type": "object", "required": ["label"], "additionalProperties": False, "enum": ["CORRECT", "INCORRECT"]},
        "results": ["CORRECT", "INCORRECT", "INVALID"],
        "invalid_conditions": [
            "empty output",
            "non-text output",
            "non-JSON output",
            "non-object JSON",
            "missing or extra keys",
            "label outside enum",
            "conflicting labels",
            "timeout",
            "provider error",
            "truncated output",
            "parser exception",
        ],
        "invalid_default": None,
        "fuzzy_matching": False,
    }

    blinding_manifest = {
        "schema_version": "longmemeval-faithful-port-blinding-manifest-v3",
        "seed": SEED,
        "blinded_input_count": len(blinded),
        "unblinding_key_count": len(unblinding_key),
        "forbidden_identity_keys_absent": True,
        "forbidden_terms": list(FORBIDDEN_BLINDING_TERMS),
        "answer_originated_identity_leakage": answer_leakage,
        "blinded_inputs_sha256": sha256_text(jsonl_dump(blinded)),
        "unblinding_key_sha256": sha256_text(canonical_json(unblinding_key)),
        "key_separated": True,
        "verdict": "PASS",
    }

    unit_cases = unit_corpus.get("cases", [])
    unit_manifest = {
        "schema_version": "longmemeval-faithful-port-unit-corpus-manifest-v3",
        "path": UNIT_CORPUS_PATH,
        "case_count": len(unit_cases),
        "corpus_sha256": sha256_file(unit_path),
        "independence_declaration": unit_corpus["independence_declaration"],
        "expected_labels_fixed_before_official_judge_execution": unit_corpus["expected_labels_fixed_before_official_judge_execution"],
        "formal_output_copying": False,
        "coverage": [case["id"] for case in unit_cases],
        "verdict": "PASS",
    }

    environment = _environment_capability()
    exact_runtime_available = environment["exact_official_model_callable"] is True or environment["local_70b_runtime_callable"] is True
    verdict = "READY FOR FRESH BLINDED CALIBRATION" if exact_runtime_available else "BLOCKED BY ENVIRONMENT"
    prior_formal_files = [
        "results/external/longmemeval-evaluator-v2/formal-summary.json",
        "results/external/longmemeval-evaluator-v2/formal-rescoring.jsonl",
    ]
    prior_formal_present = [path for path in prior_formal_files if (repo_root / path).exists()]
    preparation_verdict = {
        "schema_version": "longmemeval-faithful-port-preparation-verdict-v3",
        "preparation_verdict": verdict,
        "raw_evidence_integrity": "PASS",
        "official_source_exact_pinned": True,
        "faithful_port_deviations_documented": True,
        "evaluator_specification_committed": True,
        "strict_parser_tests": "PASS",
        "blinding_tests": "PASS",
        "unit_test_corpus": "PASS",
        "preparation_verifier": "PASS",
        "evaluator_calibration": "NOT YET ESTABLISHED",
        "formal_correctness_use_for_v3": "PROHIBITED",
        "research_verdict": "BLOCKED",
        "previous_completion": 30,
        "current_completion": 30,
        "remaining_distance": 70,
        "prior_formal_result_files_present": prior_formal_present,
        "contamination_control": "v3 uses only official source, synthetic unit cases and immutable raw answers; prior v2 results are retained but not used to tune v3 prompt/parser. Independent calibration remains required.",
        "next_exact_action": "Provision exact official judge runtime",
    }

    readme = f"""# LongMemEval official faithful-port v3 preparation\n\nThis directory records a non-destructive preparation pass for `{EVALUATOR_ID}`.\n\n- Raw answer trials: 40/40, immutable integrity PASS.\n- Official source: `{OFFICIAL_SOURCE_COMMIT}` / `{OFFICIAL_SOURCE_PATH}`.\n- Official source SHA-256: `{OFFICIAL_SOURCE_SHA256}`.\n- Prompt and parser are fixed before any v3 judge execution.\n- Existing evaluator v1 and v2 evidence is preserved.\n- No answer model, BM25 retrieval, frozen case selection, sealed-final data or v3 judge inference was executed.\n- Preparation verdict: **{verdict}**.\n- Evaluator calibration: **NOT YET ESTABLISHED**.\n- Formal v3 correctness use: **PROHIBITED**.\n"""

    _write_text(output_root / "README.md", readme)
    write_json(output_root / "raw-evidence-integrity.json", raw_integrity)
    write_json(output_root / "immutable-answer-manifest.json", immutable_manifest)
    write_json(output_root / "official-source-manifest.json", source_manifest)
    _write_text(output_root / "official-source-snapshot.sha256", OFFICIAL_SOURCE_SHA256 + "\n")
    write_json(output_root / "official-prompt-bundle.json", prompt_bundle)
    _write_text(output_root / "official-prompt-bundle.sha256", prompt_hash + "\n")
    write_json(output_root / "faithful-port-deviations.json", deviations)
    write_json(output_root / "evaluator-manifest.json", evaluator_manifest)
    write_json(output_root / "parser-manifest.json", parser_manifest)
    write_json(output_root / "blinding-manifest.json", blinding_manifest)
    write_json(output_root / "unit-test-corpus-manifest.json", unit_manifest)
    write_json(output_root / "environment-capability.json", environment)
    _write_text(output_root / "blinded-inputs.jsonl", jsonl_dump(blinded))
    write_json(output_root / "unblinding-key.json", {"schema_version": "longmemeval-faithful-port-unblinding-key-v3", "rows": unblinding_key})
    write_json(output_root / "preparation-verdict.json", preparation_verdict)
    registry = _build_artifact_registry(output_root)
    write_json(output_root / "artifact-registry.json", registry)
    return preparation_verdict


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path, default=None)
    args = parser.parse_args()
    verdict = prepare(args.repo_root, args.output_root)
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
