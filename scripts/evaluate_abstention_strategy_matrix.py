#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from personal_state_engine import candidate_v2 as v2
from personal_state_engine.zero_cost_baselines import _stem, cosine_overlap, parse_timestamp, recency, tokens

EXPECTED = {
    "development": "b7ef7dd716a7fe444244a1337fc8ebdb0cebdb697c8944d7881ea7e159e86807",
    "validation": "f396fa3cbc2dbb46fb7003fb7a359e7392469e45cb3abb07c0c9f7c6f01b08fa",
    "withheld": "0f7f04afd9e968df657b89b30316802cd8cb789b3f45d54e959ea2a52099882c",
}
V2_FREEZE = "d627f61d0888306a97f3ef0b78aa29dc00c444bb"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_cases(path: Path, expected_sha: str) -> list[dict[str, Any]]:
    observed = sha256_file(path)
    if observed != expected_sha:
        raise RuntimeError(f"benchmark SHA mismatch for {path}: {observed}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    if not isinstance(cases, list) or not cases:
        raise RuntimeError(f"no cases in {path}")
    return cases


def content_tokens(text: str) -> list[str]:
    return v2.content_tokens(text)


def scored_memories(case: dict[str, Any]) -> list[dict[str, Any]]:
    q_content = set(content_tokens(case["query"]))
    n_docs = max(len(case["memories"]), 1)
    query_df: Counter[str] = Counter()
    for memory in case["memories"]:
        memory_terms = set(content_tokens(memory["text"]))
        for term in q_content & memory_terms:
            query_df[term] += 1
    query_idf = {term: math.log((1 + n_docs) / (1 + query_df.get(term, 0))) + 1.0 for term in q_content}
    query_idf_total = sum(query_idf.values()) or 1.0
    rows: list[dict[str, Any]] = []
    for index, memory in enumerate(case["memories"]):
        text = memory["text"]
        raw_tokens = tokens(text)
        memory_stems = {_stem(token) for token in raw_tokens}
        memory_content = set(content_tokens(text))
        similarity = min(cosine_overlap(text, case["query"]), v2.SIMILARITY_CAP)
        base = v2.BASE_SIMILARITY_WEIGHT * similarity + v2.BASE_CONSTANT + v2.RECENCY_WEIGHT * recency(memory)
        if memory_stems & v2.STRONG_UPDATE_STEMS:
            update_bonus = v2.STRONG_UPDATE_BONUS
        elif memory_stems & v2.WEAK_UPDATE_STEMS:
            update_bonus = v2.WEAK_UPDATE_BONUS
        else:
            update_bonus = 0.0
        overlap = q_content & memory_content
        coverage = sum(query_idf[token] for token in overlap) / query_idf_total if q_content else 0.0
        novel = memory_content - q_content
        anchor_bonus = v2.RARE_ANCHOR_WEIGHT * coverage
        novel_bonus = min(len(novel), v2.NOVEL_BONUS_TOKEN_CAP) * v2.NOVEL_BONUS_PER_TOKEN if overlap else 0.0
        content_raw = [_stem(token) for token in raw_tokens if token not in v2.STOPWORDS and len(_stem(token)) > 1]
        query_only_fraction = sum(token in q_content for token in content_raw) / len(content_raw) if content_raw else 0.0
        repetition = 1.0 - len(set(content_raw)) / len(content_raw) if content_raw else 0.0
        begins_question = bool(raw_tokens and raw_tokens[0] in v2.QUESTION_WORDS)
        echo_like = coverage >= v2.ECHO_ANCHOR_THRESHOLD and len(novel) <= v2.ECHO_NOVEL_TOKEN_MAX and (
            text.strip().endswith("?") or begins_question or (
                query_only_fraction >= v2.ECHO_QUERY_ONLY_THRESHOLD and repetition >= v2.ECHO_REPETITION_THRESHOLD
            )
        )
        echo_penalty = v2.ECHO_PENALTY if echo_like else 0.0
        adversarial_penalty = v2.ADVERSARIAL_CUE_PENALTY if v2.ADVERSARIAL_STEMS & memory_stems else 0.0
        score = round(base + update_bonus + anchor_bonus + novel_bonus - echo_penalty - adversarial_penalty, 6)
        rows.append({
            "id": memory["id"], "score": score, "coverage": coverage,
            "timestamp": parse_timestamp(memory.get("timestamp")), "index_tiebreak": -index,
        })
    rows.sort(key=lambda row: (row["score"], row["timestamp"], row["index_tiebreak"], row["id"]), reverse=True)
    return rows


def features(case: dict[str, Any]) -> dict[str, Any]:
    rows = scored_memories(case)
    if not rows:
        return {"ranking": [], "top1_score": float("-inf"), "margin": float("-inf"), "coverage": 0.0}
    top1 = rows[0]
    margin = top1["score"] - rows[1]["score"] if len(rows) > 1 else top1["score"]
    return {
        "ranking": [row["id"] for row in rows[:5]],
        "top1_score": float(top1["score"]),
        "margin": float(margin),
        "coverage": float(top1["coverage"]),
    }


def retrieve_for(strategy: str, params: tuple[float, ...], feat: dict[str, Any]) -> bool:
    if strategy == "always_retrieve":
        return True
    if strategy == "absolute_score_threshold":
        return feat["top1_score"] >= params[0]
    if strategy == "top1_top2_margin":
        return feat["margin"] >= params[0]
    if strategy == "evidence_coverage_gate":
        return feat["coverage"] >= params[0]
    if strategy == "combined_confidence_gate":
        return feat["top1_score"] >= params[0] and feat["margin"] >= params[1] and feat["coverage"] >= params[2]
    raise ValueError(strategy)


def evaluate(cases: list[dict[str, Any]], strategy: str, params: tuple[float, ...]) -> dict[str, Any]:
    answerable = [case for case in cases if case["relevant_memory_ids"]]
    no_evidence = [case for case in cases if not case["relevant_memory_ids"]]
    correct_abstentions = false_retrieval = false_abstention = top1_hits = top5_hits = 0
    decisions_correct = 0
    details = []
    for case in cases:
        feat = features(case)
        retrieve = retrieve_for(strategy, params, feat)
        relevant = set(case["relevant_memory_ids"])
        if relevant:
            if not retrieve:
                false_abstention += 1
            else:
                top1 = bool(feat["ranking"] and feat["ranking"][0] in relevant)
                top5 = bool(relevant.intersection(feat["ranking"][:5]))
                top1_hits += int(top1)
                top5_hits += int(top5)
                decisions_correct += int(top1)
        else:
            if retrieve:
                false_retrieval += 1
            else:
                correct_abstentions += 1
                decisions_correct += 1
        details.append({
            "case_id": case["id"], "answerable": bool(relevant), "retrieve": retrieve,
            "top1_score": feat["top1_score"], "margin": feat["margin"], "coverage": feat["coverage"],
            "ranking": feat["ranking"],
        })
    na = len(answerable)
    nn = len(no_evidence)
    return {
        "case_count": len(cases), "answerable_case_count": na, "no_evidence_case_count": nn,
        "abstention_accuracy": correct_abstentions / nn if nn else None,
        "false_retrieval_rate": false_retrieval / nn if nn else None,
        "false_abstention_rate": false_abstention / na if na else None,
        "answerable_recall_at_1": top1_hits / na if na else None,
        "answerable_recall_at_5": top5_hits / na if na else None,
        "overall_decision_accuracy": decisions_correct / len(cases),
        "details": details,
    }


def candidates_for(strategy: str, protocol: dict[str, Any]) -> list[tuple[float, ...]]:
    grids = protocol["development_only_grids"]
    if strategy == "always_retrieve":
        return [tuple()]
    if strategy in {"absolute_score_threshold", "top1_top2_margin", "evidence_coverage_gate"}:
        return [(float(value),) for value in grids[strategy]]
    g = grids["combined_confidence_gate"]
    return [tuple(float(v) for v in values) for values in itertools.product(
        g["absolute_score_threshold"], g["top1_top2_margin"], g["evidence_coverage_gate"]
    )]


def choose_development(strategy: str, cases: list[dict[str, Any]], protocol: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for params in candidates_for(strategy, protocol):
        result = evaluate(cases, strategy, params)
        if result["false_abstention_rate"] != 0.0:
            continue
        threshold_sum = sum(params)
        key = (
            float(result["abstention_accuracy"] or 0.0),
            -float(result["false_retrieval_rate"] or 0.0),
            threshold_sum,
            tuple(-v for v in params),
        )
        rows.append((key, params, result))
    if not rows:
        raise RuntimeError(f"no development-safe parameters for {strategy}")
    rows.sort(key=lambda row: row[0], reverse=True)
    _, params, result = rows[0]
    return {"selected_params": list(params), "development": result, "eligible_configuration_count": len(rows)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if protocol.get("status") != "FROZEN_BEFORE_MULTI_STRATEGY_RESULTS":
        raise RuntimeError("protocol not frozen pre-result")
    if protocol["candidate"]["freeze_commit"] != V2_FREEZE or protocol["candidate"]["candidate_changed"] is not False:
        raise RuntimeError("candidate lock mismatch")
    if protocol["integrity"]["sealed_final_accessed"] is not False or float(protocol["integrity"]["new_monetary_cost_usd"]) != 0.0:
        raise RuntimeError("integrity/cost boundary invalid")
    splits = {name: load_cases(args.root / f"{name}.json", EXPECTED[name]) for name in EXPECTED}
    strategies = protocol["strategies"]
    outputs: dict[str, Any] = {}
    for strategy in strategies:
        chosen = choose_development(strategy, splits["development"], protocol)
        params = tuple(float(v) for v in chosen["selected_params"])
        chosen["validation"] = evaluate(splits["validation"], strategy, params)
        chosen["withheld_observed_auxiliary"] = evaluate(splits["withheld"], strategy, params)
        outputs[strategy] = chosen
    summary = {
        "schema_version": "abstention-strategy-matrix-results-v1",
        "protocol_sha256": sha256_file(args.protocol),
        "benchmark_sha256": EXPECTED,
        "candidate_v2_freeze_commit": V2_FREEZE,
        "candidate_changed": False,
        "strategies": outputs,
        "withheld_status": protocol["benchmark"]["withheld_status_for_this_new_matrix"],
        "selection_data": "development only",
        "validation_retuning": False,
        "withheld_retuning": False,
        "algorithm_parity": "NO",
        "sealed_final_accessed": False,
        "new_monetary_cost_usd": 0.0,
        "claim_boundary": protocol["claim_boundary"],
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    result_path = args.output_root / "results.json"
    write_json(result_path, summary)
    registry = {
        "schema_version": "abstention-strategy-matrix-artifact-registry-v1",
        "artifact_count": 1,
        "protocol_sha256": sha256_file(args.protocol),
        "candidate_v2_freeze_commit": V2_FREEZE,
        "new_monetary_cost_usd": 0.0,
        "sealed_final_accessed": False,
        "artifacts": [{
            "path": result_path.as_posix(), "bytes": result_path.stat().st_size,
            "sha256": sha256_file(result_path),
            "generation_command": "python scripts/evaluate_abstention_strategy_matrix.py ..."
        }],
    }
    write_json(args.output_root / "artifact-registry.json", registry)
    print(json.dumps({"status": "ABSTENTION_STRATEGY_MATRIX_COMPLETE", "selected": {k:v["selected_params"] for k,v in outputs.items()}}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
