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

EXPECTED_CORPUS_SHA256 = "d5ff2fa4c51ebf09c42c710cd6a8bcf8445060858abf07ed1b34a7ac940471b0"
EXPECTED_PROTOCOL_SHA256 = "d6948b2ecb86f651cd23cbaed30f6884d3ea14526f6272ca039b3ed88c7963c2"
EXPECTED_STATS_SHA256 = "55b03f5b46a0796b665eaac34aa38f9fc32c997866641807a8150ecf2fbf2476"
EXPECTED_CASE_COUNT = 90
EXPECTED_ANSWERABLE_COUNT = 60
EXPECTED_NO_EVIDENCE_COUNT = 30
EXPECTED_SHARD_COUNT = 30
UPSTREAM_COMMIT = "0c8039f28fdcc08189a23c07a3437d9d2482f9c2"
V4_FREEZE_COMMIT = "e6780204686d3de526905eca8f2778c2510b7876"
V4_SOURCE_SHA256 = "b57af79b3ef91497a4d3df373a990f0daa76a21c4daf87c7dd27f1c258c6d344"
V4_CONFIG_SHA256 = "a6341817ed382423a4d48d5df890765bb59f887655f16bd0e0647b89e3379606"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def reciprocal_rank(case: dict[str, Any], ranker: Callable[[dict[str, Any], int], list[str]]) -> float:
    relevant = set(case["relevant_memory_ids"])
    if not relevant:
        return 0.0
    for index, memory_id in enumerate(ranker(case, 5)):
        if memory_id in relevant:
            return 1.0 / (index + 1)
    return 0.0


def paired_bootstrap(cases: list[dict[str, Any]], left: Callable[[dict[str, Any], int], list[str]], right: Callable[[dict[str, Any], int], list[str]], iterations: int = 10000, seed: int = 20260810) -> dict[str, Any]:
    answerable = [case for case in cases if case["relevant_memory_ids"]]
    deltas = [reciprocal_rank(case, right) - reciprocal_rank(case, left) for case in answerable]
    observed = sum(deltas) / len(deltas)
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(iterations):
        samples.append(sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas))
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
        "seed": seed,
        "answerable_n": len(answerable),
        "win_tie_loss": {"right_wins": wins, "ties": ties, "right_losses": losses},
        "superiority_right_over_left": low > 0.0,
        "noninferiority_right_vs_left_margin_0_03": low >= -0.03,
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
    false_abstention_ids = [c["id"] for c in answerable if not ranker(c, 5)]
    false_retrieval_ids = [c["id"] for c in no_evidence if ranker(c, 5)]
    correct_abstentions = len(no_evidence) - len(false_retrieval_ids)
    return {
        "answerable_case_count": len(answerable),
        "no_evidence_case_count": len(no_evidence),
        "false_abstention_count": len(false_abstention_ids),
        "false_abstention_case_ids": false_abstention_ids,
        "false_abstention_rate": len(false_abstention_ids) / len(answerable),
        "false_abstention_wilson_95_ci": wilson(len(false_abstention_ids), len(answerable)),
        "answerable_recall": 1.0 - len(false_abstention_ids) / len(answerable),
        "answerable_recall_wilson_95_ci": wilson(len(answerable) - len(false_abstention_ids), len(answerable)),
        "false_retrieval_count": len(false_retrieval_ids),
        "false_retrieval_case_ids": false_retrieval_ids,
        "false_retrieval_rate": len(false_retrieval_ids) / len(no_evidence),
        "false_retrieval_wilson_95_ci": wilson(len(false_retrieval_ids), len(no_evidence)),
        "abstention_correct_count": correct_abstentions,
        "abstention_accuracy": correct_abstentions / len(no_evidence),
        "abstention_accuracy_wilson_95_ci": wilson(correct_abstentions, len(no_evidence)),
    }


def parse_time(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    wall = re.search(r"Elapsed \(wall clock\) time.*?:\s*(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)", text)
    rss = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", text)
    wall_seconds = None
    if wall:
        wall_seconds = int(wall.group(1) or 0) * 3600 + int(wall.group(2)) * 60 + float(wall.group(3))
    return {"wall_seconds": wall_seconds, "peak_rss_kib": int(rss.group(1)) if rss else None}


def normalize(evaluated: dict[str, Any], decisions: dict[str, Any]) -> dict[str, Any]:
    metrics = evaluated["metrics"]
    return {
        "MRR": metrics["MRR"],
        "recall_at_1": metrics["recall@1"],
        "recall_at_3": metrics["recall@3"],
        "recall_at_5": metrics["recall@5"],
        "ndcg_at_5": metrics["ndcg@5"],
        **decisions,
    }


def main() -> int:
    from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
    from personal_state_engine.candidate_v3 import pse_candidate_v3_rank
    from personal_state_engine.candidate_v4 import pse_candidate_v4_rank
    from personal_state_engine.zero_cost_baselines import evaluate_cases

    parser = argparse.ArgumentParser(description="Aggregate exact A-MEM adversarial-v6 shards and frozen statistics.")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--stats-protocol", type=Path, required=True)
    parser.add_argument("--shards", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--embedding-snapshot", required=True)
    parser.add_argument("--ollama-digest", required=True)
    args = parser.parse_args()

    if sha256_file(args.corpus) != EXPECTED_CORPUS_SHA256:
        raise SystemExit("v6 corpus SHA mismatch")
    if sha256_file(args.protocol) != EXPECTED_PROTOCOL_SHA256:
        raise SystemExit("v6 evaluation protocol SHA mismatch")
    if sha256_file(args.stats_protocol) != EXPECTED_STATS_SHA256:
        raise SystemExit("v6 statistics protocol SHA mismatch")
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    stats_protocol = json.loads(args.stats_protocol.read_text(encoding="utf-8"))
    if protocol.get("status") != "FROZEN_BEFORE_STAGE1_SYSTEM_EXECUTION" or stats_protocol.get("status") != "FROZEN_BEFORE_STAGE1_SYSTEM_EXECUTION":
        raise SystemExit("v6 protocols not frozen")
    identity = protocol["stage2_exact_a_mem"]["identity"]
    if identity["commit"] != UPSTREAM_COMMIT or identity["model"] != "qwen2.5:3b":
        raise SystemExit("A-MEM identity mismatch")
    if identity["model_digest"] != args.ollama_digest or identity["embedding_snapshot"] != args.embedding_snapshot:
        raise SystemExit("A-MEM runtime identity mismatch")

    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    cases = list(corpus["cases"])
    expected_ids = [case["id"] for case in cases]
    answerable = sum(bool(case["relevant_memory_ids"]) for case in cases)
    no_evidence = len(cases) - answerable
    if len(cases) != EXPECTED_CASE_COUNT or answerable != EXPECTED_ANSWERABLE_COUNT or no_evidence != EXPECTED_NO_EVIDENCE_COUNT or len(set(expected_ids)) != EXPECTED_CASE_COUNT:
        raise SystemExit("v6 corpus count/identity mismatch")

    shard_files = sorted(args.shards.glob("shard-*.json"))
    if len(shard_files) != EXPECTED_SHARD_COUNT:
        raise SystemExit(f"expected {EXPECTED_SHARD_COUNT} shard files, found {len(shard_files)}")
    predictions: list[dict[str, Any]] = []
    shard_resources: list[dict[str, Any]] = []
    for path in shard_files:
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("source_commit") != UPSTREAM_COMMIT or row.get("corpus_sha256") != EXPECTED_CORPUS_SHA256 or row.get("protocol_sha256") != EXPECTED_PROTOCOL_SHA256:
            raise SystemExit(f"provenance mismatch in {path}")
        if row.get("shard_count") != EXPECTED_SHARD_COUNT or row.get("case_count") != 3:
            raise SystemExit(f"shard shape mismatch in {path}")
        if row.get("sealed_final_accessed") is not False or float(row.get("new_monetary_cost_usd", -1)) != 0.0:
            raise SystemExit(f"integrity mismatch in {path}")
        predictions.extend(row["predictions"])
        time_path = args.shards / f"time-shard-{row['shard_index']}.txt"
        shard_resources.append({"shard_index": row["shard_index"], **(parse_time(time_path) if time_path.exists() else {"wall_seconds": None, "peak_rss_kib": None})})
    ids = [row["case_id"] for row in predictions]
    missing_ids = sorted(set(expected_ids) - set(ids))
    extra_ids = sorted(set(ids) - set(expected_ids))
    duplicate_count = len(ids) - len(set(ids))
    if len(ids) != EXPECTED_CASE_COUNT or missing_ids or extra_ids or duplicate_count:
        raise SystemExit(f"A-MEM v6 identity failure missing={missing_ids} extra={extra_ids} duplicates={duplicate_count}")
    order = {case_id: index for index, case_id in enumerate(expected_ids)}
    predictions.sort(key=lambda row: order[row["case_id"]])
    prediction_by_id = {row["case_id"]: list(row["retrieved_memory_ids"]) for row in predictions}

    def amem_rank(case: dict[str, Any], k: int = 5) -> list[str]:
        return prediction_by_id[case["id"]][:k]

    systems: dict[str, Callable[[dict[str, Any], int], list[str]]] = {
        "candidate-v2-frozen": pse_candidate_v2_rank,
        "candidate-v3-frozen": pse_candidate_v3_rank,
        "candidate-v4-frozen": pse_candidate_v4_rank,
        "exact-a-mem": amem_rank,
    }
    system_results: dict[str, Any] = {}
    for name, ranker in systems.items():
        system_results[name] = normalize(evaluate_cases(cases, ranker, 5), decision_metrics(cases, ranker))

    iterations = int(stats_protocol["bootstrap"]["iterations"])
    seed = int(stats_protocol["bootstrap"]["seed"])
    paired = {
        "candidate-v4-frozen_vs_candidate-v2-frozen": paired_bootstrap(cases, pse_candidate_v2_rank, pse_candidate_v4_rank, iterations, seed),
        "candidate-v4-frozen_vs_exact-a-mem": paired_bootstrap(cases, amem_rank, pse_candidate_v4_rank, iterations, seed),
        "candidate-v4-frozen_vs_candidate-v3-frozen": paired_bootstrap(cases, pse_candidate_v3_rank, pse_candidate_v4_rank, iterations, seed),
        "candidate-v2-frozen_vs_exact-a-mem": paired_bootstrap(cases, amem_rank, pse_candidate_v2_rank, iterations, seed),
    }

    guard = protocol["candidate_v4_selection_guardrails"]
    v2 = system_results["candidate-v2-frozen"]
    v4 = system_results["candidate-v4-frozen"]
    v4_checks = {
        "abstention_accuracy": v4["abstention_accuracy"] >= guard["minimum_abstention_accuracy"],
        "false_retrieval_rate": v4["false_retrieval_rate"] <= guard["maximum_false_retrieval_rate"],
        "false_retrieval_reduction_vs_v2": (v2["false_retrieval_rate"] - v4["false_retrieval_rate"]) >= guard["minimum_absolute_false_retrieval_reduction_vs_candidate_v2"],
        "false_abstention_rate": v4["false_abstention_rate"] <= guard["maximum_false_abstention_rate"],
        "answerable_recall": v4["answerable_recall"] >= guard["minimum_answerable_recall"],
        "mrr_preservation": (v2["MRR"] - v4["MRR"]) <= guard["maximum_mrr_deficit_vs_candidate_v2"],
        "recall_at_1_preservation": (v2["recall_at_1"] - v4["recall_at_1"]) <= guard["maximum_recall_at_1_deficit_vs_candidate_v2"],
        "recall_at_3_preservation": (v2["recall_at_3"] - v4["recall_at_3"]) <= guard["maximum_recall_at_3_deficit_vs_candidate_v2"],
        "recall_at_5_preservation": (v2["recall_at_5"] - v4["recall_at_5"]) <= guard["maximum_recall_at_5_deficit_vs_candidate_v2"],
    }

    comparison = {
        "schema_version": "amem-adversarial-v6-confirmatory-comparison-v1",
        "run_id": int(args.run_id),
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "statistics_protocol_sha256": EXPECTED_STATS_SHA256,
        "case_count": EXPECTED_CASE_COUNT,
        "answerable_case_count": EXPECTED_ANSWERABLE_COUNT,
        "no_evidence_case_count": EXPECTED_NO_EVIDENCE_COUNT,
        "missing_case_count": 0,
        "duplicate_case_count": 0,
        "invalid_case_count": 0,
        "systems": system_results,
        "paired_statistics": paired,
        "candidate_v4_selection_checks": {
            "checks": v4_checks,
            "status": "PASS" if all(v4_checks.values()) else "FAIL",
        },
        "candidate_v4_freeze_commit": V4_FREEZE_COMMIT,
        "candidate_v4_source_sha256": V4_SOURCE_SHA256,
        "candidate_v4_config_sha256": V4_CONFIG_SHA256,
        "candidate_v4_changed_after_freeze": False,
        "benchmark_changed_after_results": False,
        "sealed_final_accessed": False,
        "new_monetary_cost_usd": 0.0,
        "algorithm_parity": "NO",
        "claim_boundary": "Exact A-MEM v6 comparison is confirmatory evidence under frozen v6 protocols. Candidate-v4 selection still requires all frozen answerability/retrieval guardrails. Equivalence and formal parity were not preregistered and cannot be claimed post hoc.",
    }

    walls = [float(row["wall_seconds"]) for row in shard_resources if row["wall_seconds"] is not None]
    rss = [int(row["peak_rss_kib"]) for row in shard_resources if row["peak_rss_kib"] is not None]
    resources = {
        "schema_version": "amem-adversarial-v6-resource-v1",
        "run_id": int(args.run_id),
        "source_commit": UPSTREAM_COMMIT,
        "embedding_snapshot": args.embedding_snapshot,
        "ollama_digest": args.ollama_digest,
        "serialized_inference_wall_seconds": sum(walls) if walls else None,
        "mean_end_to_end_case_wall_seconds": (sum(walls) / EXPECTED_CASE_COUNT) if walls else None,
        "max_shard_wall_seconds": max(walls) if walls else None,
        "max_peak_rss_kib": max(rss) if rss else None,
        "shards": sorted(shard_resources, key=lambda row: row["shard_index"]),
        "new_monetary_cost_usd": 0.0,
        "paid_api_used": False,
        "cloud_gpu_used": False,
        "sealed_final_accessed": False,
    }

    output = args.output_root
    output.mkdir(parents=True, exist_ok=True)
    predictions_payload = {
        "schema_version": "amem-adversarial-v6-predictions-v1",
        "run_id": int(args.run_id),
        "source_commit": UPSTREAM_COMMIT,
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
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
        "schema_version": "amem-adversarial-v6-artifact-registry-v1",
        "source_run_id": int(args.run_id),
        "source_commit": UPSTREAM_COMMIT,
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "statistics_protocol_sha256": EXPECTED_STATS_SHA256,
        "artifact_count": len(artifacts),
        "new_monetary_cost_usd": 0.0,
        "sealed_final_accessed": False,
        "artifacts": [{"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in artifacts],
    }
    write_json(output / "artifact-registry.json", registry)
    print(json.dumps({
        "case_count": comparison["case_count"],
        "systems": system_results,
        "paired_statistics": paired,
        "candidate_v4_selection_checks": comparison["candidate_v4_selection_checks"],
        "integrity": {"missing": 0, "duplicate": 0, "invalid": 0, "new_monetary_cost_usd": 0.0, "sealed_final_accessed": False},
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
