#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v4 import answerability_signature, pse_candidate_v4_rank
from personal_state_engine.zero_cost_baselines import evaluate_cases

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/personal_state_engine/candidate_v4.py"
CONFIG = ROOT / "experiments/protocols/candidate-v4-config-v1.json"
PREREG = ROOT / "experiments/protocols/candidate-v4-design-preregistration-v2.json"
EXPECTED_SOURCE_SHA256 = "b57af79b3ef91497a4d3df373a990f0daa76a21c4daf87c7dd27f1c258c6d344"
EXPECTED_CONFIG_SHA256 = "a6341817ed382423a4d48d5df890765bb59f887655f16bd0e0647b89e3379606"
EXPECTED_PREREG_SHA256 = "e1d8b1a75e80946ad04917aa06c0450784fa11f96c2e1f916c49371860121442"
FREEZE_COMMIT = "e6780204686d3de526905eca8f2778c2510b7876"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_frozen_identity() -> None:
    expected = {
        SOURCE: EXPECTED_SOURCE_SHA256,
        CONFIG: EXPECTED_CONFIG_SHA256,
        PREREG: EXPECTED_PREREG_SHA256,
    }
    for path, digest in expected.items():
        actual = sha256(path)
        if actual != digest:
            raise RuntimeError(f"frozen identity mismatch: {path.relative_to(ROOT)} {actual} != {digest}")


def decision_metrics(
    cases: list[dict[str, Any]],
    ranker: Callable[[dict[str, Any], int], list[str]],
) -> dict[str, Any]:
    answerable = [case for case in cases if case["relevant_memory_ids"]]
    no_evidence = [case for case in cases if not case["relevant_memory_ids"]]
    false_abstentions = sum(not ranker(case, 5) for case in answerable)
    false_retrievals = sum(bool(ranker(case, 5)) for case in no_evidence)
    return {
        "answerable_case_count": len(answerable),
        "no_evidence_case_count": len(no_evidence),
        "false_abstention_count": false_abstentions,
        "false_retrieval_count": false_retrievals,
        "false_abstention_rate": false_abstentions / len(answerable) if answerable else None,
        "answerable_recall": 1.0 - false_abstentions / len(answerable) if answerable else None,
        "false_retrieval_rate": false_retrievals / len(no_evidence) if no_evidence else None,
        "abstention_accuracy": 1.0 - false_retrievals / len(no_evidence) if no_evidence else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--expected-dataset-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    verify_frozen_identity()
    dataset = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    dataset_digest = sha256(dataset)
    if dataset_digest != args.expected_dataset_sha256:
        raise RuntimeError(
            f"dataset identity mismatch: {dataset_digest} != {args.expected_dataset_sha256}"
        )

    payload = json.loads(dataset.read_text(encoding="utf-8"))
    cases = payload["cases"]
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    thresholds = prereg["acceptance_thresholds"]

    systems: dict[str, Any] = {}
    for name, ranker in (
        ("pse_candidate_v2_frozen", pse_candidate_v2_rank),
        ("pse_candidate_v4_frozen", pse_candidate_v4_rank),
    ):
        systems[name] = {
            **evaluate_cases(cases, ranker, 5),
            "decision_metrics": decision_metrics(cases, ranker),
        }

    v2 = systems["pse_candidate_v2_frozen"]["metrics"]
    v4 = systems["pse_candidate_v4_frozen"]["metrics"]
    d = systems["pse_candidate_v4_frozen"]["decision_metrics"]
    checks = {
        "abstention_accuracy": d["abstention_accuracy"] >= thresholds["minimum_abstention_accuracy"],
        "false_retrieval_rate": d["false_retrieval_rate"] <= thresholds["maximum_false_retrieval_rate"],
        "false_abstention_rate": d["false_abstention_rate"] <= thresholds["maximum_false_abstention_rate"],
        "mrr_preservation": (v2["MRR"] - v4["MRR"]) <= thresholds["maximum_mrr_deficit_vs_candidate_v2"],
        "recall_at_1_preservation": (v2["recall@1"] - v4["recall@1"]) <= thresholds["maximum_recall_at_1_deficit_vs_candidate_v2"],
        "recall_at_3_preservation": (v2["recall@3"] - v4["recall@3"]) <= thresholds["maximum_recall_at_3_deficit_vs_candidate_v2"],
        "recall_at_5_preservation": (v2["recall@5"] - v4["recall@5"]) <= thresholds["maximum_recall_at_5_deficit_vs_candidate_v2"],
    }
    signatures = [
        {
            "case_id": case["id"],
            **answerability_signature(case, pse_candidate_v2_rank(case, 5)),
        }
        for case in cases
    ]
    result = {
        "schema_version": "candidate-v4-protected-validation-result-v2",
        "execution": "ONE_TIME_FROZEN_VALIDATION",
        "candidate_v4_freeze_commit": FREEZE_COMMIT,
        "candidate_v4_source_sha256": EXPECTED_SOURCE_SHA256,
        "candidate_v4_config_sha256": EXPECTED_CONFIG_SHA256,
        "effective_preregistration_sha256": EXPECTED_PREREG_SHA256,
        "dataset_path": str(dataset.relative_to(ROOT)),
        "dataset_sha256": dataset_digest,
        "case_count": len(cases),
        "systems": systems,
        "guardrail_checks": checks,
        "acceptance": "PASS" if all(checks.values()) else "FAIL",
        "answerability_signatures": signatures,
        "integrity": {
            "old_contaminated_validation_used": False,
            "candidate_v4_changed_after_freeze": False,
            "sealed_final_content_accessed": False,
            "new_monetary_cost_usd": 0.0,
        },
        "claim_boundary": "One-time non-sealed protected validation only; PASS permits creation of a new v6 confirmatory benchmark but does not itself complete Gate E or establish parity or superiority.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "acceptance": result["acceptance"],
        "guardrail_checks": checks,
        "candidate_v4_decision_metrics": d,
        "candidate_v2_metrics": v2,
        "candidate_v4_metrics": v4,
    }, indent=2, sort_keys=True))
    return 0 if result["acceptance"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
