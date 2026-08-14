#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
from pathlib import Path
from typing import Any, Callable

EXPECTED_CORPUS_SHA256 = "41313c3da5f49e87a4456686e90c4b6934c4c088685f31679cc639b66ecbf169"
EXPECTED_CASE_COUNT = 60
EXPECTED_ANSWERABLE_COUNT = 45
EXPECTED_NO_EVIDENCE_COUNT = 15
EXPECTED_SHARD_COUNT = 20
UPSTREAM_COMMIT = "0c8039f28fdcc08189a23c07a3437d9d2482f9c2"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rr(case: dict[str, Any], ranker: Callable[[dict[str, Any], int], list[str]]) -> float:
    relevant = set(case["relevant_memory_ids"])
    if not relevant:
        return 0.0
    for i, memory_id in enumerate(ranker(case, 5)):
        if memory_id in relevant:
            return 1.0 / (i + 1)
    return 0.0


def paired_bootstrap(cases: list[dict[str, Any]], left: Callable[[dict[str, Any], int], list[str]], right: Callable[[dict[str, Any], int], list[str]], iterations: int = 10000) -> dict[str, Any]:
    answerable = [case for case in cases if case["relevant_memory_ids"]]
    deltas = [rr(case, right) - rr(case, left) for case in answerable]
    observed = sum(deltas) / len(deltas)
    rng = random.Random(20260810)
    samples = []
    for _ in range(iterations):
        sample = [deltas[rng.randrange(len(deltas))] for _ in deltas]
        samples.append(sum(sample) / len(sample))
    samples.sort()
    low = samples[math.floor(0.025 * (iterations - 1))]
    high = samples[math.ceil(0.975 * (iterations - 1))]
    wins = sum(delta > 0 for delta in deltas)
    ties = sum(delta == 0 for delta in deltas)
    losses = sum(delta < 0 for delta in deltas)
    return {
        "right_minus_left_mrr_delta": observed,
        "bootstrap_95_ci": [low, high],
        "iterations": iterations,
        "answerable_n": len(answerable),
        "win_tie_loss": {"right_wins": wins, "ties": ties, "right_losses": losses},
    }


def wilson(successes: int, n: int, z: float = 1.959963984540054) -> list[float] | None:
    if n == 0:
        return None
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [centre - half, centre + half]


def decision_metrics(cases: list[dict[str, Any]], ranker: Callable[[dict[str, Any], int], list[str]]) -> dict[str, Any]:
    answerable = [c for c in cases if c["relevant_memory_ids"]]
    no_evidence = [c for c in cases if not c["relevant_memory_ids"]]
    false_abstentions = sum(not ranker(c, 5) for c in answerable)
    false_retrievals = sum(bool(ranker(c, 5)) for c in no_evidence)
    abstention_successes = len(no_evidence) - false_retrievals
    return {
        "answerable_case_count": len(answerable),
        "no_evidence_case_count": len(no_evidence),
        "false_abstention_count": false_abstentions,
        "false_abstention_rate": false_abstentions / len(answerable),
        "false_abstention_wilson_95_ci": wilson(false_abstentions, len(answerable)),
        "false_retrieval_count": false_retrievals,
        "false_retrieval_rate": false_retrievals / len(no_evidence),
        "false_retrieval_wilson_95_ci": wilson(false_retrievals, len(no_evidence)),
        "abstention_correct_count": abstention_successes,
        "abstention_accuracy": abstention_successes / len(no_evidence),
        "abstention_accuracy_wilson_95_ci": wilson(abstention_successes, len(no_evidence)),
    }


def parse_time(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    wall = re.search(r"Elapsed \(wall clock\) time.*?:\s*(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)", text)
    rss = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", text)
    wall_seconds = None
    if wall:
        wall_seconds = int(wall.group(1) or 0) * 3600 + int(wall.group(2)) * 60 + float(wall.group(3))
    return {"wall_seconds": wall_seconds, "peak_rss_kib": int(rss.group(1)) if rss else None}


def normalize(result: dict[str, Any], decisions: dict[str, Any]) -> dict[str, Any]:
    metrics = result["metrics"]
    return {
        "mrr": metrics["MRR"],
        "recall_at_1": metrics["recall@1"],
        "recall_at_3": metrics["recall@3"],
        "recall_at_5": metrics["recall@5"],
        "ndcg_at_5": metrics["ndcg@5"],
        **decisions,
    }


def main() -> int:
    from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
    from personal_state_engine.candidate_v3 import pse_candidate_v3_rank
    from personal_state_engine.zero_cost_baselines import evaluate_cases, pse_candidate_v1_rank, pse_current_rank

    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--shards", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--embedding-snapshot", required=True)
    parser.add_argument("--ollama-digest", required=True)
    args = parser.parse_args()

    if sha256_file(args.corpus) != EXPECTED_CORPUS_SHA256:
        raise SystemExit("v5 corpus SHA mismatch")
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if protocol.get("status") != "FROZEN_BEFORE_ANY_V5_SYSTEM_RESULT":
        raise SystemExit("v5 protocol status mismatch")
    if protocol["benchmark"]["materialized_dataset_expected_sha256"] != EXPECTED_CORPUS_SHA256:
        raise SystemExit("v5 protocol dataset hash mismatch")
    if protocol["stage_2_exact_a_mem"]["commit"] != UPSTREAM_COMMIT:
        raise SystemExit("A-MEM source mismatch")

    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    cases = list(corpus["cases"])
    expected_ids = [case["id"] for case in cases]
    answerable = sum(bool(case["relevant_memory_ids"]) for case in cases)
    no_evidence = len(cases) - answerable
    if len(cases) != EXPECTED_CASE_COUNT or answerable != EXPECTED_ANSWERABLE_COUNT or no_evidence != EXPECTED_NO_EVIDENCE_COUNT or len(set(expected_ids)) != EXPECTED_CASE_COUNT:
        raise SystemExit("v5 corpus count/identity mismatch")

    shard_files = sorted(args.shards.glob("shard-*.json"))
    if len(shard_files) != EXPECTED_SHARD_COUNT:
        raise SystemExit(f"expected {EXPECTED_SHARD_COUNT} shard files, found {len(shard_files)}")
    predictions: list[dict[str, Any]] = []
    shard_resources = []
    protocol_sha = sha256_file(args.protocol)
    for path in shard_files:
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("source_commit") != UPSTREAM_COMMIT or row.get("corpus_sha256") != EXPECTED_CORPUS_SHA256 or row.get("protocol_sha256") != protocol_sha:
            raise SystemExit(f"provenance mismatch in {path}")
        if row.get("sealed_final_accessed") is not False or float(row.get("new_monetary_cost_usd", -1)) != 0.0:
            raise SystemExit(f"integrity mismatch in {path}")
        predictions.extend(row["predictions"])
        time_path = args.shards / f"time-shard-{row['shard_index']}.txt"
        shard_resources.append({"shard_index": row["shard_index"], **(parse_time(time_path) if time_path.exists() else {"wall_seconds": None, "peak_rss_kib": None})})
    ids = [row["case_id"] for row in predictions]
    if len(ids) != EXPECTED_CASE_COUNT or len(set(ids)) != EXPECTED_CASE_COUNT or set(ids) != set(expected_ids):
        raise SystemExit("A-MEM v5 has missing, duplicate, or extra cases")
    order = {case_id: index for index, case_id in enumerate(expected_ids)}
    predictions.sort(key=lambda row: order[row["case_id"]])
    prediction_by_id = {row["case_id"]: list(row["retrieved_memory_ids"]) for row in predictions}

    def amem_rank(case: dict[str, Any], k: int = 5) -> list[str]:
        return prediction_by_id[case["id"]][:k]

    systems = {
        "pse_current_reconstruction": pse_current_rank,
        "pse_candidate_v1": pse_candidate_v1_rank,
        "pse_candidate_v2_frozen": pse_candidate_v2_rank,
        "pse_candidate_v3_frozen": pse_candidate_v3_rank,
        "a_mem_exact": amem_rank,
    }
    system_results = {}
    for name, ranker in systems.items():
        evaluated = evaluate_cases(cases, ranker, 5)
        system_results[name] = normalize(evaluated, decision_metrics(cases, ranker))

    paired = {
        "candidate_v3_vs_candidate_v2": paired_bootstrap(cases, pse_candidate_v2_rank, pse_candidate_v3_rank),
        "candidate_v3_vs_exact_a_mem": paired_bootstrap(cases, amem_rank, pse_candidate_v3_rank),
        "candidate_v3_vs_candidate_v1": paired_bootstrap(cases, pse_candidate_v1_rank, pse_candidate_v3_rank),
        "candidate_v3_vs_current": paired_bootstrap(cases, pse_current_rank, pse_candidate_v3_rank),
    }

    v2 = system_results["pse_candidate_v2_frozen"]
    v3 = system_results["pse_candidate_v3_frozen"]
    thresholds = protocol["gate_e_selection_rule"]
    v5_retrieval_pass = (v2["mrr"] - v3["mrr"]) <= thresholds["v5_retrieval_guardrail"]["maximum_allowed_mrr_deficit_vs_candidate_v2"]
    abst = thresholds["v5_abstention_requirements"]
    v5_abstention_pass = (
        v3["abstention_accuracy"] >= abst["candidate_v3_abstention_accuracy_at_least"]
        and v3["false_retrieval_rate"] <= abst["candidate_v3_false_retrieval_rate_at_most"]
        and v3["false_abstention_rate"] <= abst["candidate_v3_false_abstention_rate_at_most"]
    )

    comparison = {
        "schema_version": "amem-adversarial-v5-confirmatory-comparison-v1",
        "run_id": int(args.run_id),
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "protocol_sha256": protocol_sha,
        "case_count": EXPECTED_CASE_COUNT,
        "answerable_case_count": EXPECTED_ANSWERABLE_COUNT,
        "no_evidence_case_count": EXPECTED_NO_EVIDENCE_COUNT,
        "systems": system_results,
        "paired_statistics": paired,
        "power_status": "SUFFICIENT" if EXPECTED_ANSWERABLE_COUNT >= protocol["benchmark"]["minimum_power_answerable_n"] else "UNDERPOWERED",
        "candidate_v3_v5_selection_checks": {
            "retrieval_guardrail": "PASS" if v5_retrieval_pass else "FAIL",
            "abstention_requirements": "PASS" if v5_abstention_pass else "FAIL",
            "candidate_selection_status": "V5_THRESHOLDS_PASS" if v5_retrieval_pass and v5_abstention_pass else "REJECTED_BY_FROZEN_V5_THRESHOLDS",
        },
        "candidate_v3_changed_after_freeze": False,
        "candidate_v2_changed": False,
        "operator_designed": True,
        "independent_reproduction": False,
        "sealed_final_accessed": False,
        "new_monetary_cost_usd": 0.0,
        "algorithm_parity": "NO",
        "claim_boundary": protocol["claim_boundary"],
    }

    walls = [float(row["wall_seconds"]) for row in shard_resources if row["wall_seconds"] is not None]
    rss = [int(row["peak_rss_kib"]) for row in shard_resources if row["peak_rss_kib"] is not None]
    resources = {
        "schema_version": "amem-adversarial-v5-resource-v1",
        "run_id": int(args.run_id),
        "source_commit": UPSTREAM_COMMIT,
        "embedding_snapshot": args.embedding_snapshot,
        "ollama_digest": args.ollama_digest,
        "serialized_inference_wall_seconds": sum(walls) if walls else None,
        "mean_end_to_end_case_wall_seconds": (sum(walls) / EXPECTED_CASE_COUNT) if walls else None,
        "max_shard_wall_seconds": max(walls) if walls else None,
        "max_peak_rss_kib": max(rss) if rss else None,
        "shards": shard_resources,
        "new_monetary_cost_usd": 0.0,
        "paid_api_used": False,
        "cloud_gpu_used": False,
        "sealed_final_accessed": False,
    }

    output = args.output_root
    output.mkdir(parents=True, exist_ok=True)
    predictions_payload = {
        "schema_version": "amem-adversarial-v5-predictions-v1",
        "run_id": int(args.run_id),
        "source_commit": UPSTREAM_COMMIT,
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "protocol_sha256": protocol_sha,
        "embedding_snapshot": args.embedding_snapshot,
        "ollama_digest": args.ollama_digest,
        "case_count": EXPECTED_CASE_COUNT,
        "predictions": predictions,
        "sealed_final_accessed": False,
        "new_monetary_cost_usd": 0.0,
    }
    write_json(output / "predictions-run1.json", predictions_payload)
    write_json(output / "comparison-run1.json", comparison)
    write_json(output / "resource-summary-run1.json", resources)
    artifacts = [output / "predictions-run1.json", output / "comparison-run1.json", output / "resource-summary-run1.json"]
    registry = {
        "schema_version": "amem-adversarial-v5-artifact-registry-v1",
        "source_run_id": int(args.run_id),
        "source_commit": UPSTREAM_COMMIT,
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "protocol_sha256": protocol_sha,
        "artifact_count": len(artifacts),
        "new_monetary_cost_usd": 0.0,
        "sealed_final_accessed": False,
        "artifacts": [{"path": path.as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in artifacts],
    }
    write_json(output / "artifact-registry.json", registry)
    print(json.dumps({"status": "AMEM_ADVERSARIAL_V5_COMPLETE", "run_id": int(args.run_id), "candidate_v3_selection": comparison["candidate_v3_v5_selection_checks"], "a_mem": system_results["a_mem_exact"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
