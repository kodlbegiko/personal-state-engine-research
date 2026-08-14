from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v6 import pse_candidate_v6_rank

EXPECTED_DATASET_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
EXPECTED_SPLIT_CASE_IDS_SHA256 = "1ca053112b634871d24addbb3982d4e417dc8f4acce10609554cc41b6ed8e987"
EXPECTED_CASE_COUNT = 99
EXPECTED_CANDIDATE_V6_SOURCE_SHA256 = "c540056c6f30f0145ab8ef8c10be3abcae2ed24e6a087a2d9a3531bc5e545325"
EXPECTED_CANDIDATE_V6_CONFIG_SHA256 = "067bfa64d97bf2eb1f7208082c36d202118a0e50a2414fc345bf328f83cab5b1"
BOOTSTRAP_ITERATIONS = 10_000
BOOTSTRAP_SEED = 20260814
NONINFERIORITY_MARGIN = 0.03


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def adapt_row(raw: dict[str, Any]) -> dict[str, Any]:
    required = {
        "question_id", "question_type", "question", "question_date",
        "haystack_session_ids", "haystack_dates", "haystack_sessions",
        "answer_session_ids",
    }
    missing = required.difference(raw)
    if missing:
        raise ValueError(f"missing fields: {sorted(missing)}")
    qid = raw["question_id"]
    if not isinstance(qid, str) or not qid:
        raise ValueError("question_id must be non-empty string")
    question = raw["question"]
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"{qid}: question must be non-empty string")
    session_ids = raw["haystack_session_ids"]
    dates = raw["haystack_dates"]
    sessions = raw["haystack_sessions"]
    if not (isinstance(session_ids, list) and isinstance(dates, list) and isinstance(sessions, list)):
        raise ValueError(f"{qid}: session fields must be lists")
    if not (len(session_ids) == len(dates) == len(sessions)):
        raise ValueError(f"{qid}: session arrays must align")

    official_abstention = qid.endswith("_abs")
    memories: list[dict[str, Any]] = []
    relevant: list[str] = []
    for sidx, (session_id, timestamp, turns) in enumerate(zip(session_ids, dates, sessions, strict=True)):
        if not isinstance(turns, list):
            raise ValueError(f"{qid}: session {sidx} turns must be list")
        for tidx, turn in enumerate(turns):
            if not isinstance(turn, dict):
                raise ValueError(f"{qid}: turn must be object")
            role = turn.get("role")
            text = turn.get("content")
            if role not in {"user", "assistant"} or not isinstance(text, str):
                raise ValueError(f"{qid}: invalid turn schema")
            memory_id = f"{qid}::s{sidx}::t{tidx}"
            memories.append({"id": memory_id, "text": text, "timestamp": timestamp})
            if bool(turn.get("has_answer", False)) and not official_abstention:
                relevant.append(memory_id)

    if not memories:
        raise ValueError(f"{qid}: empty history")
    if official_abstention:
        relevant = []
    elif not relevant:
        raise ValueError(f"{qid}: answerable case has no has_answer evidence turn")

    return {
        "id": qid,
        "category": raw["question_type"],
        "query": question,
        "memories": memories,
        "relevant_memory_ids": relevant,
        "official_abstention": official_abstention,
    }


def load_sealed_cases(dataset_path: Path, split_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    dataset_bytes = dataset_path.read_bytes()
    dataset_sha = sha256_bytes(dataset_bytes)
    if dataset_sha != EXPECTED_DATASET_SHA256:
        raise ValueError(f"dataset sha mismatch: {dataset_sha}")
    split_bytes = split_path.read_bytes()
    split = json.loads(split_bytes)
    if split.get("case_count") != EXPECTED_CASE_COUNT:
        raise ValueError("sealed split case count mismatch")
    if split.get("case_ids_sha256") != EXPECTED_SPLIT_CASE_IDS_SHA256:
        raise ValueError("sealed split case_ids_sha256 mismatch")
    case_ids = split.get("case_ids")
    if not isinstance(case_ids, list) or len(case_ids) != EXPECTED_CASE_COUNT or len(set(case_ids)) != EXPECTED_CASE_COUNT:
        raise ValueError("sealed split IDs incomplete or duplicated")

    raw_rows = json.loads(dataset_bytes)
    if not isinstance(raw_rows, list):
        raise ValueError("official dataset root must be list")
    by_id: dict[str, dict[str, Any]] = {}
    for raw in raw_rows:
        if not isinstance(raw, dict) or not isinstance(raw.get("question_id"), str):
            raise ValueError("official dataset contains invalid row")
        qid = raw["question_id"]
        if qid in by_id:
            raise ValueError(f"duplicate dataset question_id: {qid}")
        by_id[qid] = raw
    missing = [qid for qid in case_ids if qid not in by_id]
    if missing:
        raise ValueError(f"sealed IDs missing from dataset: {len(missing)}")
    cases = [adapt_row(by_id[qid]) for qid in case_ids]
    return cases, {
        "dataset_sha256": dataset_sha,
        "split_file_sha256": sha256_bytes(split_bytes),
        "case_ids_sha256": split["case_ids_sha256"],
        "case_count": len(cases),
        "answerable_count": sum(bool(c["relevant_memory_ids"]) for c in cases),
        "no_evidence_count": sum(not bool(c["relevant_memory_ids"]) for c in cases),
    }


def reciprocal_rank(case: dict[str, Any], ranking: list[str]) -> float:
    relevant = set(case["relevant_memory_ids"])
    if not relevant:
        return 0.0
    return next((1.0 / (idx + 1) for idx, mid in enumerate(ranking) if mid in relevant), 0.0)


def recall_at(case: dict[str, Any], ranking: list[str], depth: int) -> float:
    relevant = set(case["relevant_memory_ids"])
    if not relevant:
        return 0.0
    return len(relevant.intersection(ranking[:depth])) / len(relevant)


def evaluate_ranker(cases: list[dict[str, Any]], ranker: Callable[[dict[str, Any], int], list[str]]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    rows: dict[str, dict[str, Any]] = {}
    answerable_rows: list[dict[str, Any]] = []
    no_evidence_rows: list[dict[str, Any]] = []
    for case in cases:
        ranking = ranker(case, 5)
        row = {
            "rr": reciprocal_rank(case, ranking),
            "r1": recall_at(case, ranking, 1),
            "r3": recall_at(case, ranking, 3),
            "r5": recall_at(case, ranking, 5),
            "output_nonempty": bool(ranking),
            "retrieved_count": len(ranking),
            "relevant_count": len(case["relevant_memory_ids"]),
        }
        rows[case["id"]] = row
        (answerable_rows if case["relevant_memory_ids"] else no_evidence_rows).append(row)

    def mean(key: str) -> float:
        return sum(float(row[key]) for row in answerable_rows) / len(answerable_rows) if answerable_rows else 0.0

    answered = sum(bool(row["output_nonempty"]) for row in answerable_rows)
    false_retrievals = sum(bool(row["output_nonempty"]) for row in no_evidence_rows)
    metrics = {
        "MRR": mean("rr"),
        "R@1": mean("r1"),
        "R@3": mean("r3"),
        "R@5": mean("r5"),
        "answerable_recall": answered / len(answerable_rows) if answerable_rows else 1.0,
        "false_abstention": 1.0 - (answered / len(answerable_rows) if answerable_rows else 1.0),
        "false_retrieval_count": false_retrievals,
        "no_evidence_false_retrieval": false_retrievals / len(no_evidence_rows) if no_evidence_rows else None,
        "abstention_accuracy": 1.0 - (false_retrievals / len(no_evidence_rows)) if no_evidence_rows else None,
    }
    return metrics, rows


def paired_bootstrap(v2_rows: dict[str, dict[str, Any]], v6_rows: dict[str, dict[str, Any]], answerable_ids: list[str]) -> dict[str, Any]:
    deltas = [float(v6_rows[qid]["rr"]) - float(v2_rows[qid]["rr"]) for qid in answerable_ids]
    if not deltas:
        raise ValueError("no answerable cases for bootstrap")
    point = sum(deltas) / len(deltas)
    rng = random.Random(BOOTSTRAP_SEED)
    samples: list[float] = []
    for _ in range(BOOTSTRAP_ITERATIONS):
        draw = [deltas[rng.randrange(len(deltas))] for _ in deltas]
        samples.append(sum(draw) / len(draw))
    samples.sort()
    lo = samples[int(0.025 * (len(samples) - 1))]
    hi = samples[int(0.975 * (len(samples) - 1))]
    return {
        "iterations": BOOTSTRAP_ITERATIONS,
        "seed": BOOTSTRAP_SEED,
        "margin": NONINFERIORITY_MARGIN,
        "point_delta_mrr": point,
        "bootstrap_mean_delta_mrr": sum(samples) / len(samples),
        "ci95": [lo, hi],
        "fraction_delta_ge_minus_margin": sum(x >= -NONINFERIORITY_MARGIN for x in samples) / len(samples),
        "noninferiority_pass": lo >= -NONINFERIORITY_MARGIN,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source_path = ROOT / "src" / "personal_state_engine" / "candidate_v6.py"
    config_path = ROOT / "experiments" / "configs" / "candidate-v6-v1.json"
    source_sha = file_sha256(source_path)
    config_sha = file_sha256(config_path)
    if source_sha != EXPECTED_CANDIDATE_V6_SOURCE_SHA256:
        raise SystemExit(f"candidate-v6 source identity mismatch: {source_sha}")
    if config_sha != EXPECTED_CANDIDATE_V6_CONFIG_SHA256:
        raise SystemExit(f"candidate-v6 config identity mismatch: {config_sha}")

    cases, integrity = load_sealed_cases(args.dataset, args.split)
    v2_metrics, v2_rows = evaluate_ranker(cases, pse_candidate_v2_rank)
    v6_metrics, v6_rows = evaluate_ranker(cases, pse_candidate_v6_rank)
    answerable_ids = [case["id"] for case in cases if case["relevant_memory_ids"]]
    no_evidence_ids = [case["id"] for case in cases if not case["relevant_memory_ids"]]
    stats = paired_bootstrap(v2_rows, v6_rows, answerable_ids)

    deficits = {
        "MRR": v2_metrics["MRR"] - v6_metrics["MRR"],
        "R@1": v2_metrics["R@1"] - v6_metrics["R@1"],
        "R@3": v2_metrics["R@3"] - v6_metrics["R@3"],
        "R@5": v2_metrics["R@5"] - v6_metrics["R@5"],
    }
    reduction = None
    if v2_metrics["no_evidence_false_retrieval"] is not None and v6_metrics["no_evidence_false_retrieval"] is not None:
        reduction = v2_metrics["no_evidence_false_retrieval"] - v6_metrics["no_evidence_false_retrieval"]
    checks = {
        "mrr_deficit": deficits["MRR"] <= 0.03 + 1e-12,
        "r1_deficit": deficits["R@1"] <= 0.03 + 1e-12,
        "r3_deficit": deficits["R@3"] <= 0.02 + 1e-12,
        "r5_deficit": deficits["R@5"] <= 0.02 + 1e-12,
        "answerable_recall": v6_metrics["answerable_recall"] >= 0.95 - 1e-12,
        "false_abstention": v6_metrics["false_abstention"] <= 0.05 + 1e-12,
        "bootstrap_noninferiority": bool(stats["noninferiority_pass"]),
    }
    if no_evidence_ids:
        checks.update({
            "abstention_accuracy": float(v6_metrics["abstention_accuracy"]) >= 0.90 - 1e-12,
            "no_evidence_false_retrieval": float(v6_metrics["no_evidence_false_retrieval"]) <= 0.10 + 1e-12,
            "false_retrieval_reduction": reduction is not None and reduction >= 0.70 - 1e-12,
        })

    wins = ties = losses = 0
    per_case: list[dict[str, Any]] = []
    for case in cases:
        qid = case["id"]
        if case["relevant_memory_ids"]:
            delta = float(v6_rows[qid]["rr"]) - float(v2_rows[qid]["rr"])
            if delta > 1e-12:
                wins += 1
            elif delta < -1e-12:
                losses += 1
            else:
                ties += 1
        per_case.append({
            "case_id": qid,
            "official_abstention": not bool(case["relevant_memory_ids"]),
            "relevant_count": len(case["relevant_memory_ids"]),
            "candidate_v2": v2_rows[qid],
            "candidate_v6": v6_rows[qid],
        })

    result = {
        "schema_version": "gate-f-sealed-final-evaluation-v1",
        "phase": "FORMAL_GATE_F_SINGLE_EXECUTION",
        "candidate": {
            "name": "candidate-v6",
            "source_sha256": source_sha,
            "config_sha256": config_sha,
            "modified": False,
        },
        "sealed_final": integrity,
        "metrics": {"candidate_v2": v2_metrics, "candidate_v6": v6_metrics},
        "retrieval_deficits_vs_candidate_v2": deficits,
        "no_evidence_false_retrieval_absolute_reduction_vs_candidate_v2": reduction,
        "statistics": stats,
        "wins_ties_losses": {"wins": wins, "ties": ties, "losses": losses, "answerable_total": len(answerable_ids)},
        "guardrails": {"checks": checks, "pass": all(checks.values())},
        "integrity": {
            "expected_cases": EXPECTED_CASE_COUNT,
            "observed_cases": len(cases),
            "missing": 0,
            "duplicate": 0,
            "invalid": 0,
            "paid_api": False,
            "paid_gpu": False,
            "paid_inference": False,
            "new_monetary_cost_usd": 0,
        },
        "per_case_nonsemantic_evidence": per_case,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "per_case_nonsemantic_evidence"}, indent=2, sort_keys=True))
    return 0 if result["guardrails"]["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
