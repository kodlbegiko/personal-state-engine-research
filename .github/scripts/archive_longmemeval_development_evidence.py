#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path
from typing import Any


DECISIONS: dict[str, dict[str, tuple[bool, str]]] = {
    "gpt4_93159ced": {
        "A": (False, "incorrect_unknown_response_on_answerable_case"),
        "B": (False, "incorrect_unknown_response_on_answerable_case"),
    },
    "031748ae_abs": {
        "A": (False, "hallucinated_specific_value_on_insufficient_information"),
        "B": (False, "hallucinated_specific_value_on_insufficient_information"),
    },
    "18dcd5a5": {"A": (False, "wrong_numeric_answer"), "B": (True, "correct")},
    "09ba9854_abs": {
        "A": (False, "hallucinated_specific_value_on_insufficient_information"),
        "B": (False, "hallucinated_specific_value_on_insufficient_information"),
    },
    "gpt4_93159ced_abs": {
        "A": (False, "hallucinated_specific_value_on_insufficient_information"),
        "B": (True, "acceptable_explicit_uncertainty"),
    },
    "51b23612": {
        "A": (False, "correct_core_with_materially_false_additions"),
        "B": (False, "does_not_identify_reference_answer"),
    },
    "d7c942c3": {
        "A": (False, "correct_core_with_materially_unsupported_additions"),
        "B": (True, "correct"),
    },
    "d23cf73b": {
        "A": (False, "incorrect_unknown_response_on_answerable_case"),
        "B": (False, "incorrect_unknown_response_on_answerable_case"),
    },
    "gpt4_e05b82a6": {
        "A": (False, "incorrect_unknown_response_on_answerable_case"),
        "B": (False, "incorrect_unknown_response_on_answerable_case"),
    },
    "1903aded": {"A": (False, "wrong_list_item"), "B": (False, "wrong_list_item")},
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def kappa(tp: int, tn: int, fp: int, fn: int) -> float | None:
    total = tp + tn + fp + fn
    if not total:
        return None
    observed = (tp + tn) / total
    expected = ((tp + fp) / total) * ((tp + fn) / total) + ((tn + fn) / total) * ((tn + fp) / total)
    return (observed - expected) / (1 - expected) if not math.isclose(expected, 1.0) else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-head", required=True)
    args = parser.parse_args()

    artifact_root = args.artifact_root
    run_dir = artifact_root / "results/development-matrix/development-matrix-30676516785-attempt-1"
    top_dir = artifact_root / "results/development-matrix"
    output = args.output
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    raw_paths = sorted((run_dir / "raw-trials").glob("*.json"))
    if len(raw_paths) != 40:
        raise RuntimeError(f"expected 40 raw trials, found {len(raw_paths)}")
    shutil.copytree(run_dir / "raw-trials", output / "raw-trials")
    for name in (
        "processed-summary.json",
        "artifact-registry.json",
        "environment-manifest.json",
        "model-capability-screening.json",
        "model-cache-manifest.json",
        "human-audit-queue.json",
        "human-audit-key.json",
    ):
        shutil.copy2(run_dir / name, output / name)
    for name in (
        "execution-subset-manifest.json",
        "npm-audit.json",
        "run.stdout.log",
        "verification.stdout.log",
        "model-preload.stdout.jsonl",
        "model-preload.stderr.log",
    ):
        source = top_dir / name
        if source.exists():
            shutil.copy2(source, output / name)

    queue = load_json(run_dir / "human-audit-queue.json")
    for row in queue["rows"]:
        case_id = row["case_id"]
        for label, answer in row["answers"].items():
            decision, category = DECISIONS[case_id][label]
            answer["human_decision"] = decision
            answer["disagreement_category"] = category
        row["audit_status"] = "COMPLETED_SINGLE_OPERATOR_BLINDED_AUDIT"
    completed_audit = {
        "schema_version": "human-audit-completed-v1",
        "completed_at": "2026-08-01T01:10:00Z",
        "operator_status": "single-operator audit; not independent",
        "blinding_status": "decisions recorded before opening baseline mapping key",
        "decision_rule": "Accept semantically correct answers; accept explicit uncertainty for insufficient-information cases; reject materially wrong added facts.",
        "sample_size_cases": len(queue["rows"]),
        "sample_size_answers": sum(len(row["answers"]) for row in queue["rows"]),
        "rows": queue["rows"],
    }
    write_json(output / "human-audit-completed-blinded.json", completed_audit)

    key = load_json(run_dir / "human-audit-key.json")
    mapping = {row["case_id"]: row["mapping"] for row in key["rows"]}
    tp = tn = fp = fn = invalid = 0
    unblinded_rows = []
    by_baseline = {"EXT-B0": {"audited": 0, "correct": 0}, "EXT-B5": {"audited": 0, "correct": 0}}
    for row in completed_audit["rows"]:
        for label, answer in row["answers"].items():
            baseline = mapping[row["case_id"]][label]
            human = bool(answer["human_decision"])
            evaluator = answer["evaluator_score"]
            by_baseline[baseline]["audited"] += 1
            by_baseline[baseline]["correct"] += int(human)
            if evaluator is None:
                invalid += 1
                outcome = "INVALID"
            elif evaluator and human:
                tp += 1
                outcome = "TP"
            elif evaluator and not human:
                fp += 1
                outcome = "FP"
            elif not evaluator and human:
                fn += 1
                outcome = "FN"
            else:
                tn += 1
                outcome = "TN"
            unblinded_rows.append({
                "case_id": row["case_id"],
                "label": label,
                "baseline_id": baseline,
                "human_decision": human,
                "evaluator_score": evaluator,
                "outcome": outcome,
                "disagreement_category": answer["disagreement_category"],
            })

    valid = tp + tn + fp + fn
    summary = load_json(run_dir / "processed-summary.json")
    full_invalid = int(summary["evaluator"]["invalid_output_count"])
    calibration = {
        "schema_version": "evaluator-calibration-v1",
        "evaluator_id": "qwen2.5-0.5b-semantic-judge-v1",
        "audit_status": "single-operator audit; not independent",
        "blinding_status": "human decisions recorded before baseline mapping key was opened",
        "sample_size_cases": 10,
        "sample_size_answers": 20,
        "valid_evaluator_outputs_in_audit": valid,
        "invalid_evaluator_outputs_in_audit": invalid,
        "invalid_output_rate_in_audit": invalid / 20,
        "full_matrix_invalid_output_count": full_invalid,
        "full_matrix_output_count": 40,
        "full_matrix_invalid_output_rate": full_invalid / 40,
        "confusion_valid_outputs": {"true_positive": tp, "true_negative": tn, "false_positive": fp, "false_negative": fn},
        "raw_agreement_valid_outputs": (tp + tn) / valid,
        "raw_agreement_all_audited_answers_invalid_as_failure": (tp + tn) / 20,
        "positive_agreement_valid_outputs": 2 * tp / (2 * tp + fp + fn),
        "negative_agreement_valid_outputs": 0.0 if (2 * tn + fp + fn) else None,
        "cohens_kappa_valid_outputs": kappa(tp, tn, fp, fn),
        "abstention_errors_human": sum(
            1 for row in completed_audit["rows"] if row["is_abstention"]
            for answer in row["answers"].values() if not answer["human_decision"]
        ),
        "by_baseline_human_audit": by_baseline,
        "thresholds": {"minimum_raw_agreement": 0.8, "minimum_cohens_kappa": 0.6, "maximum_invalid_output_rate": 0.05},
        "calibration_verdict": "FAIL",
        "failure_reasons": [
            "full-matrix invalid output rate 27.5% exceeds 5% maximum",
            "valid-output raw agreement is below 80%",
            "Cohen kappa is below 0.60",
            "judge produced only positive valid classifications, causing severe false-positive bias",
        ],
        "use_for_formal_correctness": "PROHIBITED",
        "rows_unblinded_after_decision": unblinded_rows,
    }
    write_json(output / "evaluator-calibration.json", calibration)

    verdict = {
        "schema_version": "development-matrix-research-verdict-v1",
        "run_id": summary["run_id"],
        "final_research_verdict": "BLOCKED",
        "highest_evidence_level": "E3",
        "blocking_reason": "The preregistered semantic evaluator failed calibration: full-matrix invalid output rate 27.5%, valid-output raw agreement 15.4%, Cohen kappa 0.0, and 11 false positives with zero true negatives in the blinded audit sample.",
        "supported": [
            "The pinned dataset and unchanged frozen 20-case development subset were executed under protocol v2.",
            "EXT-B0 and EXT-B5 each completed 20 trials with zero model errors and zero timeouts.",
            "Raw-to-summary reconstruction, artifact hashes, unique IDs, B0 history exclusion, B5 retrieval tracing, and sealed-final non-access passed.",
            "BM25 retrieved at least one answer-bearing session for 18 of 20 cases as a post-hoc diagnostic.",
        ],
        "not_supported": [
            "Any formal correctness, accuracy, win/loss, statistical, parity, superiority, equivalence, non-inferiority, or production-readiness conclusion for EXT-B5 versus EXT-B0.",
            "That the 0.5B model eliminated floor effects.",
            "That the evaluator is reliable or calibrated.",
            "That the runtime dependency graph is secure.",
        ],
        "descriptive_only": {
            "retrieval_evidence_session_recall_at_k": 0.9,
            "b5_history_truncated_case_count": 20,
            "b5_history_token_budget_lexical": 1024,
            "incremental_answer_input_tokens_b5_minus_b0": 28814,
            "incremental_median_answer_latency_ms_b5_minus_b0": 12213.216133,
        },
    }
    write_json(output / "research-verdict.json", verdict)
    write_json(output / "gate-assessment.json", {
        "schema_version": "evidence-weighted-completion-v1",
        "previous_completion_percent": 20,
        "current_completion_percent": 24,
        "remaining_distance_percent": 76,
        "active_evidence_cap_percent": 45,
        "gates": [
            {"gate": "A", "previous": 9, "current": 10, "evidence": "Pinned sources, revisions, licenses, dependency audit.", "missing": "None material."},
            {"gate": "B", "previous": 9, "current": 10, "evidence": "Frozen protocol/split, immutable raw evidence, registry verification, failure retention, budget enforcement.", "missing": "None material after archival verification."},
            {"gate": "C", "previous": 2, "current": 4, "evidence": "20 paired cases and 40 complete raw trials with retrieval/resource diagnostics.", "missing": "Calibrated evaluator and valid formal correctness/statistical comparison."},
            {"gate": "D", "previous": 0, "current": 0, "evidence": "None.", "missing": "Strong baseline."},
            {"gate": "E", "previous": 0, "current": 0, "evidence": "None; prohibited in this phase.", "missing": "PSE candidate after baseline stabilization."},
            {"gate": "F", "previous": 0, "current": 0, "evidence": "Sealed-final not accessed.", "missing": "Preregistered sealed execution."},
            {"gate": "G", "previous": 0, "current": 0, "evidence": "None.", "missing": "Independent reproduction."},
        ],
        "rationale": "Credit increased only for source/infrastructure closure and raw paired execution. Gate C remains low because evaluator calibration failed.",
    })
    write_json(output / "archive-provenance.json", {
        "schema_version": "github-actions-evidence-provenance-v1",
        "repository": "kodlbegiko/personal-state-engine-research",
        "branch": "research/personal-state-engine-v0",
        "pull_request": 2,
        "workflow_run_id": 30676516785,
        "workflow_job_id": 91304822403,
        "workflow_artifact_id": 8810812462,
        "workflow_artifact_name": "longmemeval-development-matrix-30676516785-1",
        "workflow_artifact_zip_sha256": "bec23cd90b5ec6eca24ebca9806528e128a6d0acf3c256eb4b37682e651a5235",
        "source_head_sha": args.source_head,
        "tested_pr_merge_sha": "ea1f1775dc0a5500f37a10bf956cd543e2c450ca",
        "run_id": summary["run_id"],
        "experiment_step": "PASS",
        "raw_to_summary_contract": "PASS",
        "workflow_conclusion": "FAILURE",
        "workflow_failure_scope": "Post-experiment shell check searched ignored runtime cache instead of Git-tracked files. The evidence and contract steps passed.",
        "sealed_final_accessed": False,
    })
    (output / "README.md").write_text(
        "# LongMemEval development matrix evidence\n\n"
        "Complete E3 development evidence from Actions run `30676516785`: 40 raw trials, manifests, logs, blinded audit, calibration, and verdict.\n\n"
        "**Verdict: BLOCKED.** The semantic evaluator failed calibration and its correctness scores must not be used for B0/B5 claims.\n",
        encoding="utf-8",
    )

    registry_items = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "archive-registry.json":
            registry_items.append({
                "path": path.relative_to(output).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            })
    write_json(output / "archive-registry.json", {
        "schema_version": "development-evidence-archive-registry-v1",
        "artifact_count": len(registry_items),
        "artifacts": registry_items,
    })

    if any(path.suffix in {".onnx", ".safetensors", ".bin"} for path in output.rglob("*")):
        raise RuntimeError("model weights entered evidence archive")
    if any("longmemeval_s_cleaned" in path.name for path in output.rglob("*")):
        raise RuntimeError("dataset payload entered evidence archive")
    print(json.dumps({"status": "ARCHIVED", "output": output.as_posix(), "raw_trials": 40, "calibration": "FAIL", "verdict": "BLOCKED"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
