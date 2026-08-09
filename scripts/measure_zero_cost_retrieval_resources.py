#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import time
from pathlib import Path
from typing import Any, Callable

EXPECTED_CORPUS_SHA256 = "02e3afef1e17d9d8991ea7172cbfc19ad239874c914a088c20e5de6a146f7a1d"
EXPECTED_CANDIDATE_V2_FREEZE = "d627f61d0888306a97f3ef0b78aa29dc00c444bb"
EXPECTED_CANDIDATE_V2_SOURCE = "52c8341e4317a1492ec5511907414c7deee77ef6"
ALLOWED_SYSTEMS = {
    "bm25_local",
    "tfidf_local",
    "pse_current_reconstruction",
    "pse_candidate_v1",
    "pse_candidate_v2",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
    from personal_state_engine.zero_cost_baselines import RANKERS, evaluate_cases, pse_candidate_v1_rank, pse_current_rank

    parser = argparse.ArgumentParser(description="Measure frozen zero-cost retrieval resources without changing ranking semantics.")
    parser.add_argument("--system", required=True, choices=sorted(ALLOWED_SYSTEMS))
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if sha256_file(args.corpus) != EXPECTED_CORPUS_SHA256:
        raise SystemExit("adversarial-v4 corpus SHA mismatch")
    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if manifest.get("status") != "FROZEN_BEFORE_ANY_V4_SYSTEM_EVALUATION":
        raise SystemExit("v4 manifest is not a pre-evaluation freeze")
    if manifest.get("corpus_sha256") != EXPECTED_CORPUS_SHA256 or manifest.get("case_count") != 24:
        raise SystemExit("v4 manifest corpus mismatch")
    if manifest.get("candidate_v2_freeze_commit") != EXPECTED_CANDIDATE_V2_FREEZE:
        raise SystemExit("candidate-v2 freeze mismatch")
    if manifest.get("candidate_v2_source_commit") != EXPECTED_CANDIDATE_V2_SOURCE:
        raise SystemExit("candidate-v2 source mismatch")
    if manifest.get("candidate_source_changed_for_v4") is not False or manifest.get("sealed_final_accessed") is not False:
        raise SystemExit("candidate/integrity freeze violated")
    if protocol.get("status") != "FROZEN_BEFORE_V4_SYSTEM_RESULTS":
        raise SystemExit("v4 protocol is not frozen pre-result")
    if protocol["benchmark"]["sha256"] != EXPECTED_CORPUS_SHA256:
        raise SystemExit("v4 protocol corpus mismatch")
    if protocol["candidate_lock"]["candidate_v2_freeze_commit"] != EXPECTED_CANDIDATE_V2_FREEZE:
        raise SystemExit("v4 protocol candidate lock mismatch")
    if protocol["integrity"]["sealed_final_accessed"] is not False or float(protocol["integrity"]["new_monetary_cost_usd"]) != 0.0:
        raise SystemExit("v4 protocol integrity/cost boundary invalid")

    cases = list(corpus.get("cases", []))
    if len(cases) != 24 or len({case["id"] for case in cases}) != 24:
        raise SystemExit("v4 corpus must contain exactly 24 unique cases")

    rankers: dict[str, Callable[[dict[str, Any], int], list[str]]] = {
        "bm25_local": RANKERS["bm25_local"],
        "tfidf_local": RANKERS["tfidf_local"],
        "pse_current_reconstruction": pse_current_rank,
        "pse_candidate_v1": pse_candidate_v1_rank,
        "pse_candidate_v2": pse_candidate_v2_rank,
    }
    ranker = rankers[args.system]

    before_usage = resource.getrusage(resource.RUSAGE_SELF)
    wall_start = time.perf_counter()
    cpu_start = time.process_time()
    evaluation = evaluate_cases(cases, ranker)
    cpu_seconds = time.process_time() - cpu_start
    wall_seconds = time.perf_counter() - wall_start
    after_usage = resource.getrusage(resource.RUSAGE_SELF)

    payload = {
        "schema_version": "zero-cost-retrieval-resource-measurement-v1",
        "system": args.system,
        "benchmark": "adversarial-v4-postfreeze-discrimination",
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "manifest_sha256": sha256_file(args.manifest),
        "protocol_sha256": sha256_file(args.protocol),
        "case_count": 24,
        "answerable_case_count": 22,
        "abstention_case_count": 2,
        "candidate_v2_freeze_commit": EXPECTED_CANDIDATE_V2_FREEZE,
        "candidate_v2_source_commit": EXPECTED_CANDIDATE_V2_SOURCE,
        "wall_clock_seconds": wall_seconds,
        "per_case_seconds": wall_seconds / 24.0,
        "cpu_seconds": cpu_seconds,
        "peak_rss_kib": int(after_usage.ru_maxrss),
        "minor_page_faults_delta": int(after_usage.ru_minflt - before_usage.ru_minflt),
        "major_page_faults_delta": int(after_usage.ru_majflt - before_usage.ru_majflt),
        "voluntary_context_switches_delta": int(after_usage.ru_nvcsw - before_usage.ru_nvcsw),
        "involuntary_context_switches_delta": int(after_usage.ru_nivcsw - before_usage.ru_nivcsw),
        "mrr": evaluation["metrics"].get("MRR"),
        "recall_at_1": evaluation["metrics"].get("recall@1"),
        "measurement_scope": "full 24-case frozen adversarial-v4 retrieval evaluation in one isolated process",
        "measurement_note": "Peak RSS includes Python runtime and imported package overhead. Each system is measured in a separate GitHub Actions process on ubuntu-latest; no ranking semantics are modified.",
        "new_monetary_cost_usd": 0.0,
        "paid_api_used": False,
        "paid_gpu_used": False,
        "sealed_final_accessed": False,
        "algorithm_parity": "NO",
    }
    write_json(args.output, payload)
    print(json.dumps({"status": "RESOURCE_MEASUREMENT_COMPLETE", "system": args.system, "wall_clock_seconds": wall_seconds, "peak_rss_kib": payload["peak_rss_kib"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
