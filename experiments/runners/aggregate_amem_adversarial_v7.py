from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
from pathlib import Path
from typing import Any, Callable

EXPECTED_CORPUS_SHA256 = "77f2113fdf67001c53a31f0d9eff4ecac7e71564335ab9a505665b44a05546cd"
EXPECTED_PROTOCOL_SHA256 = "d2c0b23c467175e54d325d019afaf555f5d26f09a4320aae61eee9cd65f4fdd3"
EXPECTED_STATS_SHA256 = "584e8bf8761ba414ea100df19ca53356b3ef09c0a190be82cfd2f44d5f8a194f"
EXPECTED_CASE_COUNT = 90
EXPECTED_ANSWERABLE = 60
EXPECTED_NO_EVIDENCE = 30
EXPECTED_SHARD_COUNT = 30
UPSTREAM_COMMIT = "0c8039f28fdcc08189a23c07a3437d9d2482f9c2"
V6_SOURCE_SHA256 = "c540056c6f30f0145ab8ef8c10be3abcae2ed24e6a087a2d9a3531bc5e545325"
V6_CONFIG_SHA256 = "067bfa64d97bf2eb1f7208082c36d202118a0e50a2414fc345bf328f83cab5b1"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rr(case: dict[str, Any], ranking: list[str]) -> float:
    relevant = set(case["relevant_memory_ids"])
    for i, mid in enumerate(ranking[:5], 1):
        if mid in relevant:
            return 1.0 / i
    return 0.0


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - pos) + ordered[hi] * (pos - lo)


def paired_bootstrap(cases: list[dict[str, Any]], left: Callable[[dict[str, Any], int], list[str]], right: Callable[[dict[str, Any], int], list[str]], iterations: int, seed: int) -> dict[str, Any]:
    answerable = [case for case in cases if case["relevant_memory_ids"]]
    deltas = [rr(case, left(case, 5)) - rr(case, right(case, 5)) for case in answerable]
    observed = sum(deltas) / len(deltas)
    rng = random.Random(seed)
    samples = [sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas) for _ in range(iterations)]
    low, high = percentile(samples, 0.025), percentile(samples, 0.975)
    return {
        "left_minus_right_mrr_delta": observed,
        "bootstrap_95_ci": [low, high],
        "iterations": iterations,
        "seed": seed,
        "answerable_n": len(answerable),
        "wins": sum(x > 0 for x in deltas),
        "ties": sum(x == 0 for x in deltas),
        "losses": sum(x < 0 for x in deltas),
        "superiority_left_over_right": low > 0.0,
        "noninferiority_left_vs_right_margin_0_03": low >= -0.03,
    }


def wilson(successes: int, n: int, z: float = 1.959963984540054) -> list[float]:
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1-p) / n + z*z/(4*n*n)) / denom
    return [max(0.0, centre-half), min(1.0, centre+half)]


def decision_metrics(cases: list[dict[str, Any]], ranker: Callable[[dict[str, Any], int], list[str]]) -> dict[str, Any]:
    answerable = [c for c in cases if c["relevant_memory_ids"]]
    no_evidence = [c for c in cases if not c["relevant_memory_ids"]]
    fa = [c["id"] for c in answerable if not ranker(c, 5)]
    fr = [c["id"] for c in no_evidence if ranker(c, 5)]
    return {
        "false_abstention_count": len(fa),
        "false_abstention_case_ids": fa,
        "false_abstention_rate": len(fa)/len(answerable),
        "false_abstention_wilson_95_ci": wilson(len(fa), len(answerable)),
        "answerable_recall": 1-len(fa)/len(answerable),
        "answerable_recall_wilson_95_ci": wilson(len(answerable)-len(fa), len(answerable)),
        "false_retrieval_count": len(fr),
        "false_retrieval_case_ids": fr,
        "false_retrieval_rate": len(fr)/len(no_evidence),
        "false_retrieval_wilson_95_ci": wilson(len(fr), len(no_evidence)),
        "abstention_accuracy": 1-len(fr)/len(no_evidence),
        "abstention_accuracy_wilson_95_ci": wilson(len(no_evidence)-len(fr), len(no_evidence)),
    }


def parse_time(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"wall_seconds": None, "peak_rss_kib": None}
    text = path.read_text(encoding="utf-8", errors="replace")
    wall = re.search(r"Elapsed \(wall clock\) time.*?:\s*(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)", text)
    rss = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", text)
    wall_seconds = None
    if wall:
        wall_seconds = int(wall.group(1) or 0)*3600 + int(wall.group(2))*60 + float(wall.group(3))
    return {"wall_seconds": wall_seconds, "peak_rss_kib": int(rss.group(1)) if rss else None}


def main() -> int:
    from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
    from personal_state_engine.candidate_v3 import pse_candidate_v3_rank
    from personal_state_engine.candidate_v4 import pse_candidate_v4_rank
    from personal_state_engine.candidate_v5 import pse_candidate_v5_rank
    from personal_state_engine.candidate_v6 import pse_candidate_v6_rank
    from personal_state_engine.zero_cost_baselines import evaluate_cases

    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--stats-protocol", type=Path, required=True)
    parser.add_argument("--stage1-summary", type=Path, required=True)
    parser.add_argument("--shards", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--embedding-snapshot", required=True)
    parser.add_argument("--ollama-digest", required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    stats_protocol = json.loads(args.stats_protocol.read_text(encoding="utf-8"))
    stage1 = json.loads(args.stage1_summary.read_text(encoding="utf-8"))
    if sha256_file(args.corpus) != EXPECTED_CORPUS_SHA256 or manifest["dataset_sha256"] != EXPECTED_CORPUS_SHA256:
        raise SystemExit("v7 corpus mismatch")
    if sha256_file(args.protocol) != EXPECTED_PROTOCOL_SHA256 or manifest["evaluation_protocol_sha256"] != EXPECTED_PROTOCOL_SHA256:
        raise SystemExit("v7 protocol mismatch")
    if sha256_file(args.stats_protocol) != EXPECTED_STATS_SHA256 or manifest["statistics_protocol_sha256"] != EXPECTED_STATS_SHA256:
        raise SystemExit("v7 stats protocol mismatch")
    if manifest["status"] != "FROZEN_BEFORE_ANY_SYSTEM_EXECUTION" or manifest["post_result_editing_allowed"] is not False:
        raise SystemExit("v7 manifest freeze mismatch")
    if stage1["benchmark_discrimination"]["verdict"] != "PASS" or stage1["candidate_v6_guardrails"]["verdict"] != "PASS" or stage1["stage2_exact_a_mem_authorized"] is not True:
        raise SystemExit("Stage-2 not authorized")
    identity = protocol["stage2_exact_a_mem"]["identity"]
    if identity["commit"] != UPSTREAM_COMMIT or identity["model_digest"] != args.ollama_digest or identity["embedding_snapshot"] != args.embedding_snapshot:
        raise SystemExit("A-MEM pinned identity mismatch")

    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    cases = corpus["cases"]
    expected_ids = [c["id"] for c in cases]
    if len(cases) != 90 or len(set(expected_ids)) != 90 or sum(bool(c["relevant_memory_ids"]) for c in cases) != 60:
        raise SystemExit("v7 case contract mismatch")
    case_by_id = {c["id"]: c for c in cases}

    shard_files = sorted(args.shards.glob("shard-*.json"))
    if len(shard_files) != EXPECTED_SHARD_COUNT:
        raise SystemExit(f"expected 30 shard files, found {len(shard_files)}")
    predictions: list[dict[str, Any]] = []
    resources: list[dict[str, Any]] = []
    for path in shard_files:
        row = json.loads(path.read_text(encoding="utf-8"))
        if row["source_commit"] != UPSTREAM_COMMIT or row["corpus_sha256"] != EXPECTED_CORPUS_SHA256 or row["protocol_sha256"] != EXPECTED_PROTOCOL_SHA256:
            raise SystemExit(f"provenance mismatch: {path}")
        if row["shard_count"] != 30 or row["case_count"] != 3 or row["sealed_final_accessed"] is not False or float(row["new_monetary_cost_usd"]) != 0.0:
            raise SystemExit(f"shard integrity mismatch: {path}")
        predictions.extend(row["predictions"])
        resources.append({"shard_index": row["shard_index"], **parse_time(args.shards/f"time-shard-{row['shard_index']}.txt")})

    ids = [p["case_id"] for p in predictions]
    missing = sorted(set(expected_ids)-set(ids))
    extra = sorted(set(ids)-set(expected_ids))
    duplicates = len(ids)-len(set(ids))
    invalid = 0
    for pred in predictions:
        valid_ids = {m["id"] for m in case_by_id.get(pred["case_id"], {}).get("memories", [])}
        if any(mid not in valid_ids for mid in pred["retrieved_memory_ids"]):
            invalid += 1
    if len(ids) != 90 or missing or extra or duplicates or invalid:
        raise SystemExit(f"A-MEM v7 acceptance failure missing={missing} extra={extra} duplicates={duplicates} invalid={invalid}")
    order={cid:i for i,cid in enumerate(expected_ids)}
    predictions.sort(key=lambda x: order[x["case_id"]])
    pred_by_id={p["case_id"]:p["retrieved_memory_ids"] for p in predictions}
    def amem_rank(case: dict[str, Any], k: int=5) -> list[str]:
        return pred_by_id[case["id"]][:k]

    rankers={
        "candidate-v2-frozen":pse_candidate_v2_rank,
        "candidate-v3-frozen":pse_candidate_v3_rank,
        "candidate-v4-frozen":pse_candidate_v4_rank,
        "candidate-v5-frozen":pse_candidate_v5_rank,
        "candidate-v6-frozen":pse_candidate_v6_rank,
        "exact-a-mem":amem_rank,
    }
    systems={}
    for name,ranker in rankers.items():
        e=evaluate_cases(cases,ranker,5)["metrics"]
        systems[name]={
            "MRR":e["MRR"],"R@1":e["recall@1"],"R@3":e["recall@3"],"R@5":e["recall@5"],
            **decision_metrics(cases,ranker),
        }
    iterations=int(stats_protocol["bootstrap"]["iterations"])
    seed=int(stats_protocol["bootstrap"]["seed"])
    paired={
        "candidate-v6-frozen_vs_candidate-v2-frozen":paired_bootstrap(cases,pse_candidate_v6_rank,pse_candidate_v2_rank,iterations,seed),
        "candidate-v6-frozen_vs_exact-a-mem":paired_bootstrap(cases,pse_candidate_v6_rank,amem_rank,iterations,seed),
        "candidate-v6-frozen_vs_candidate-v3-frozen":paired_bootstrap(cases,pse_candidate_v6_rank,pse_candidate_v3_rank,iterations,seed),
        "candidate-v2-frozen_vs_exact-a-mem":paired_bootstrap(cases,pse_candidate_v2_rank,amem_rank,iterations,seed),
    }

    comparison={
        "schema_version":"amem-adversarial-v7-confirmatory-comparison-v1",
        "run_id":int(args.run_id),
        "case_count":90,"answerable_case_count":60,"no_evidence_case_count":30,
        "missing_case_count":len(missing),"duplicate_case_count":duplicates,"invalid_case_count":invalid,
        "corpus_sha256":EXPECTED_CORPUS_SHA256,"protocol_sha256":EXPECTED_PROTOCOL_SHA256,"statistics_protocol_sha256":EXPECTED_STATS_SHA256,
        "candidate_v6_source_sha256":V6_SOURCE_SHA256,"candidate_v6_config_sha256":V6_CONFIG_SHA256,
        "a_mem_source_commit":UPSTREAM_COMMIT,"ollama_digest":args.ollama_digest,"embedding_snapshot":args.embedding_snapshot,
        "systems":systems,"paired_statistics":paired,
        "scientific_selection":{
            "candidate_v6_stage1_guardrails":"PASS",
            "benchmark_discrimination":"PASS",
            "exact_a_mem_90_of_90_valid":True,
            "statistics_executed":True,
            "candidate_v6_vs_exact_a_mem_noninferiority":paired["candidate-v6-frozen_vs_exact-a-mem"]["noninferiority_left_vs_right_margin_0_03"],
            "gate_e_scientific_requirements_complete":True,
        },
        "algorithm_parity":"NO",
        "algorithm_parity_reason":"No separate preregistered parity/equivalence criterion exists; non-inferiority is not equivalence.",
        "candidate_v6_changed_after_freeze":False,"benchmark_changed_after_results":False,
        "sealed_final_accessed":False,"new_monetary_cost_usd":0.0,"paid_api_used":False,"cloud_gpu_used":False,
    }
    predictions_payload={"schema_version":"amem-adversarial-v7-predictions-v1","case_count":90,"predictions":predictions}
    resource={"schema_version":"amem-adversarial-v7-resource-summary-v1","shards":resources,"new_monetary_cost_usd":0.0,"paid_api_used":False,"cloud_gpu_used":False,"sealed_final_accessed":False}
    args.output_root.mkdir(parents=True,exist_ok=True)
    write_json(args.output_root/'predictions-run1.json',predictions_payload)
    write_json(args.output_root/'comparison-run1.json',comparison)
    write_json(args.output_root/'resource-summary-run1.json',resource)
    registry={"schema_version":"amem-adversarial-v7-artifact-registry-v1","artifacts":[]}
    for name in ['predictions-run1.json','comparison-run1.json','resource-summary-run1.json']:
        p=args.output_root/name
        registry['artifacts'].append({"path":name,"bytes":p.stat().st_size,"sha256":sha256_file(p)})
    write_json(args.output_root/'artifact-registry.json',registry)
    print(json.dumps(comparison,indent=2,sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
