#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from pathlib import Path
from typing import Any, Callable

EXPECTED_CORPUS_SHA256 = "02e3afef1e17d9d8991ea7172cbfc19ad239874c914a088c20e5de6a146f7a1d"
EXPECTED_V2_FREEZE = "d627f61d0888306a97f3ef0b78aa29dc00c444bb"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize(result: dict[str, Any]) -> dict[str, Any]:
    m = result["metrics"]
    return {
        "case_count": result["case_count"],
        "answerable_case_count": result["answerable_case_count"],
        "abstention_case_count": result["abstention_case_count"],
        "mrr": m.get("MRR"),
        "recall_at_1": m.get("recall@1"),
        "recall_at_5": m.get("recall@5"),
        "ndcg_at_5": m.get("ndcg@5"),
        "irrelevant_retrieval_rate": m.get("irrelevant_retrieval_rate"),
        "abstention_accuracy": m.get("abstention_accuracy"),
    }


def perturb(cases: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    output = copy.deepcopy(cases)
    for index, case in enumerate(output, start=1):
        query = case["query"]
        if mode == "capitalization":
            case["query"] = query.upper()
        elif mode == "punctuation":
            case["query"] = f"!!! {query} ???"
        elif mode == "whitespace":
            case["query"] = "   ".join(query.split())
        elif mode == "memory_shuffle":
            rng = random.Random(31000 + index)
            rng.shuffle(case["memories"])
        elif mode == "timestamp_missing":
            for memory in case["memories"]:
                memory.pop("timestamp", None)
        elif mode == "timestamp_malformed":
            for memory in case["memories"]:
                memory["timestamp"] = "malformed-timestamp"
        elif mode == "same_timestamp":
            for memory in case["memories"]:
                memory["timestamp"] = "2026-01-01"
        elif mode == "fresh_irrelevant_distractor":
            case["memories"].append({"id": "__robust_fresh_irrelevant__", "text": "Fresh unrelated administrative note with no answer to the query.", "timestamp": "2099-01-01"})
        elif mode == "stale_distractor":
            case["memories"].append({"id": "__robust_stale__", "text": f"Obsolete unrelated reference repeating the question wording: {query}", "timestamp": "1999-01-01"})
        elif mode == "lexical_copy":
            case["memories"].append({"id": "__robust_lexical_copy__", "text": f"{query} This is an unrelated distractor and does not contain the answer.", "timestamp": "2026-08-08"})
        elif mode == "same_name_entity":
            case["memories"].append({"id": "__robust_same_name__", "text": f"{query} A different same-name person, project, room, or entity has unrelated details; this memory is not about the asked entity.", "timestamp": "2026-08-08"})
        elif mode == "duplicate_distractor_cluster":
            text = f"{query} Duplicate irrelevant cluster item; no answer is provided."
            for dup in range(3):
                case["memories"].append({"id": f"__robust_dup_{dup}__", "text": text, "timestamp": "2026-08-08"})
        elif mode == "keyword_stuffing":
            repeated = " ".join(query.split() * 3)
            case["memories"].append({"id": "__robust_keyword_stuffing__", "text": f"{repeated} unrelated distractor no answer", "timestamp": "2026-08-08"})
        else:
            raise ValueError(mode)
    return output


def top1_flip_rate(base_cases: list[dict[str, Any]], perturbed_cases: list[dict[str, Any]], ranker: Callable[[dict[str, Any], int], list[str]]) -> float:
    flips = 0
    for base, changed in zip(base_cases, perturbed_cases, strict=True):
        left = ranker(base, 1)
        right = ranker(changed, 1)
        left_id = left[0] if left else None
        right_id = right[0] if right else None
        flips += int(left_id != right_id)
    return flips / len(base_cases)


def main() -> int:
    from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
    from personal_state_engine.zero_cost_baselines import evaluate_cases, pse_candidate_v1_rank, pse_current_rank

    parser = argparse.ArgumentParser(description="Run preregistered robustness perturbations on frozen PSE candidates.")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    if sha256_file(args.corpus) != EXPECTED_CORPUS_SHA256:
        raise SystemExit("robustness base corpus SHA mismatch")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if manifest.get("status") != "FROZEN_BEFORE_ANY_V4_SYSTEM_EVALUATION" or manifest.get("candidate_v2_freeze_commit") != EXPECTED_V2_FREEZE:
        raise SystemExit("base benchmark/candidate freeze mismatch")
    if protocol.get("status") != "FROZEN_BEFORE_SUITE_RESULTS" or protocol["base_benchmark"]["sha256"] != EXPECTED_CORPUS_SHA256:
        raise SystemExit("robustness protocol is not intact pre-result freeze")
    if protocol["candidate_lock"]["candidate_v2_freeze_commit"] != EXPECTED_V2_FREEZE:
        raise SystemExit("robustness candidate lock mismatch")
    if protocol["integrity"]["sealed_final_accessed"] is not False or float(protocol["integrity"]["new_monetary_cost_usd"]) != 0.0:
        raise SystemExit("robustness integrity/cost boundary invalid")

    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    cases = list(corpus["cases"])
    if len(cases) != 24:
        raise SystemExit("expected 24 base cases")
    systems: dict[str, Callable[[dict[str, Any], int], list[str]]] = {
        "pse_current_reconstruction": pse_current_rank,
        "pse_candidate_v1": pse_candidate_v1_rank,
        "pse_candidate_v2": pse_candidate_v2_rank,
    }
    if list(systems) != protocol["systems"]:
        raise SystemExit("robustness system scope differs from protocol")

    base_results = {name: normalize(evaluate_cases(cases, ranker)) for name, ranker in systems.items()}
    perturbation_results: dict[str, Any] = {}
    worst: dict[str, dict[str, Any]] = {name: {"mode": None, "mrr_delta": 0.0, "recall_at_1_delta": 0.0} for name in systems}
    for mode in protocol["perturbations"]:
        changed = perturb(cases, mode)
        mode_rows = {}
        for name, ranker in systems.items():
            metrics = normalize(evaluate_cases(changed, ranker))
            mrr_delta = float(metrics["mrr"] or 0.0) - float(base_results[name]["mrr"] or 0.0)
            r1_delta = float(metrics["recall_at_1"] or 0.0) - float(base_results[name]["recall_at_1"] or 0.0)
            row = {**metrics, "mrr_delta_vs_base": mrr_delta, "recall_at_1_delta_vs_base": r1_delta, "top1_flip_rate": top1_flip_rate(cases, changed, ranker)}
            mode_rows[name] = row
            if mrr_delta < worst[name]["mrr_delta"]:
                worst[name] = {"mode": mode, "mrr_delta": mrr_delta, "recall_at_1_delta": r1_delta}
        perturbation_results[mode] = mode_rows

    output = {
        "schema_version": "candidate-robustness-suite-results-v1",
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "manifest_sha256": sha256_file(args.manifest),
        "protocol_sha256": sha256_file(args.protocol),
        "candidate_v2_freeze_commit": EXPECTED_V2_FREEZE,
        "case_count": 24,
        "base": base_results,
        "perturbations": perturbation_results,
        "worst_observed_mrr_delta": worst,
        "candidate_changed_for_suite": False,
        "independent_reproduction": False,
        "algorithm_parity": "NO",
        "sealed_final_accessed": False,
        "new_monetary_cost_usd": 0.0,
        "claim_boundary": protocol["claim_boundary"],
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    result_path = args.output_root / "results.json"
    write_json(result_path, output)
    registry = {
        "schema_version": "candidate-robustness-suite-artifact-registry-v1",
        "artifact_count": 1,
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "protocol_sha256": sha256_file(args.protocol),
        "candidate_v2_freeze_commit": EXPECTED_V2_FREEZE,
        "sealed_final_accessed": False,
        "new_monetary_cost_usd": 0.0,
        "artifacts": [{"path": result_path.as_posix(), "bytes": result_path.stat().st_size, "sha256": sha256_file(result_path), "generation_command": "python scripts/evaluate_candidate_robustness_suite.py ..."}],
    }
    write_json(args.output_root / "artifact-registry.json", registry)
    print(json.dumps({"status": "ROBUSTNESS_SUITE_COMPLETE", "v2_worst": worst["pse_candidate_v2"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
