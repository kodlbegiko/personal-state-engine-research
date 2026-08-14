#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable


def _dcg(relevances: list[int]) -> float:
    return sum(rel / math.log2(rank + 2) for rank, rel in enumerate(relevances))


def metrics_for_case(relevant: set[str], retrieved: list[str]) -> dict[str, float]:
    def recall_at(k: int) -> float:
        if not relevant:
            return 1.0 if not retrieved[:k] else 0.0
        return len(relevant.intersection(retrieved[:k])) / len(relevant)

    rr = 0.0
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant:
            rr = 1.0 / rank
            break
    observed = [1 if item in relevant else 0 for item in retrieved[:5]]
    ideal = [1] * min(len(relevant), 5)
    ideal_dcg = _dcg(ideal)
    ndcg = 1.0 if not relevant and not retrieved[:5] else (_dcg(observed) / ideal_dcg if ideal_dcg else 0.0)
    irrelevant_rate = 0.0 if not retrieved else sum(item not in relevant for item in retrieved) / len(retrieved)
    return {
        "recall_at_1": recall_at(1),
        "recall_at_3": recall_at(3),
        "recall_at_5": recall_at(5),
        "mrr": rr,
        "ndcg_at_5": ndcg,
        "irrelevant_retrieval_rate": irrelevant_rate,
    }


def aggregate(rows: Iterable[dict[str, float]]) -> dict[str, float]:
    rows = list(rows)
    if not rows:
        raise ValueError("no rows")
    keys = rows[0]
    return {key: sum(row[key] for row in rows) / len(rows) for key in keys}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    corpus = json.loads(Path(args.corpus).read_text())
    predictions = json.loads(Path(args.predictions).read_text())
    by_id = {row["case_id"]: row for row in predictions["predictions"]}
    details = []
    for case in corpus["cases"]:
        prediction = by_id.get(case["id"])
        if prediction is None:
            raise SystemExit(f"missing prediction for {case['id']}")
        row = metrics_for_case(set(case["relevant_memory_ids"]), list(prediction["retrieved_memory_ids"]))
        details.append({"case_id": case["id"], **row})
    payload = {
        "schema_version": "strong-baseline-retrieval-results-v1",
        "case_count": len(details),
        "aggregate": aggregate([{k: v for k, v in row.items() if k != "case_id"} for row in details]),
        "details": details,
    }
    Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
