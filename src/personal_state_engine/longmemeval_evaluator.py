from __future__ import annotations

import hashlib
import json
import math
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

OFFICIAL_SOURCE_REPOSITORY = "https://github.com/xiaowu0162/LongMemEval"
OFFICIAL_SOURCE_COMMIT = "9e0b455f4ef0e2ab8f2e582289761153549043fc"
OFFICIAL_SOURCE_PATH = "src/evaluation/evaluate_qa.py"
OFFICIAL_OPENAI_MODEL = "gpt-4o-2024-08-06"
LOCAL_FALLBACK_MODEL = "onnx-community/Llama-3.2-3B-Instruct-ONNX"
LOCAL_FALLBACK_REVISION = "cab364e7d0e1de7aa09e3abc932be92361c5b55f"

_GENERIC_TEMPLATE = (
    "I will give you a question, a correct answer, and a response from a model. "
    "Please answer yes if the response contains the correct answer. Otherwise, answer no. "
    "If the response is equivalent to the correct answer or contains all the intermediate steps "
    "to get the correct answer, you should also answer yes. If the response only contains a subset "
    "of the information required by the answer, answer no.\n\n"
    "Question: {question}\n\nCorrect Answer: {answer}\n\nModel Response: {response}\n\n"
    "Is the model response correct? Answer yes or no only."
)
_TEMPORAL_TEMPLATE = (
    "I will give you a question, a correct answer, and a response from a model. "
    "Please answer yes if the response contains the correct answer. Otherwise, answer no. "
    "If the response is equivalent to the correct answer or contains all the intermediate steps "
    "to get the correct answer, you should also answer yes. If the response only contains a subset "
    "of the information required by the answer, answer no. In addition, do not penalize off-by-one "
    "errors for the number of days. If the question asks for the number of days/weeks/months, etc., "
    "and the model makes off-by-one errors (e.g., predicting 19 days when the answer is 18), the "
    "model's response is still correct.\n\nQuestion: {question}\n\nCorrect Answer: {answer}\n\n"
    "Model Response: {response}\n\nIs the model response correct? Answer yes or no only."
)
_KNOWLEDGE_UPDATE_TEMPLATE = (
    "I will give you a question, a correct answer, and a response from a model. "
    "Please answer yes if the response contains the correct answer. Otherwise, answer no. "
    "If the response contains some previous information along with an updated answer, the response "
    "should be considered as correct as long as the updated answer is the required answer.\n\n"
    "Question: {question}\n\nCorrect Answer: {answer}\n\nModel Response: {response}\n\n"
    "Is the model response correct? Answer yes or no only."
)
_PREFERENCE_TEMPLATE = (
    "I will give you a question, a rubric for desired personalized response, and a response from a "
    "model. Please answer yes if the response satisfies the desired response. Otherwise, answer no. "
    "The model does not need to reflect all the points in the rubric. The response is correct as "
    "long as it recalls and utilizes the user's personal information correctly.\n\n"
    "Question: {question}\n\nRubric: {answer}\n\nModel Response: {response}\n\n"
    "Is the model response correct? Answer yes or no only."
)
_ABSTENTION_TEMPLATE = (
    "I will give you an unanswerable question, an explanation, and a response from a model. "
    "Please answer yes if the model correctly identifies the question as unanswerable. The model "
    "could say that the information is incomplete, or some other information is given but the asked "
    "information is not.\n\nQuestion: {question}\n\nExplanation: {answer}\n\n"
    "Model Response: {response}\n\nDoes the model correctly identify the question as unanswerable? "
    "Answer yes or no only."
)

PROMPT_TEMPLATES = {
    "generic": _GENERIC_TEMPLATE,
    "temporal-reasoning": _TEMPORAL_TEMPLATE,
    "knowledge-update": _KNOWLEDGE_UPDATE_TEMPLATE,
    "single-session-preference": _PREFERENCE_TEMPLATE,
    "abstention": _ABSTENTION_TEMPLATE,
}

STRICT_YES_NO_PATTERN = re.compile(r"^\s*(yes|no)\s*[.!]?\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedJudgment:
    status: str
    correct: bool | None
    normalized_text: str | None
    error: str | None


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def prompt_templates_sha256() -> str:
    return sha256_text(canonical_json(PROMPT_TEMPLATES))


def build_official_prompt(
    question_type: str,
    question: str,
    reference_answer: str,
    candidate_answer: str,
    *,
    abstention: bool,
) -> str:
    if abstention:
        template = _ABSTENTION_TEMPLATE
    elif question_type in {"single-session-user", "single-session-assistant", "multi-session"}:
        template = _GENERIC_TEMPLATE
    elif question_type == "temporal-reasoning":
        template = _TEMPORAL_TEMPLATE
    elif question_type == "knowledge-update":
        template = _KNOWLEDGE_UPDATE_TEMPLATE
    elif question_type == "single-session-preference":
        template = _PREFERENCE_TEMPLATE
    else:
        raise ValueError(f"unsupported LongMemEval question type: {question_type}")
    return template.format(question=question, answer=reference_answer, response=candidate_answer)


def parse_strict_yes_no(text: str) -> ParsedJudgment:
    if not isinstance(text, str):
        return ParsedJudgment("INVALID", None, None, "judge output is not text")
    match = STRICT_YES_NO_PATTERN.fullmatch(text)
    if not match:
        return ParsedJudgment(
            "INVALID",
            None,
            None,
            "judge output must be exactly yes or no, optionally followed by one period or exclamation mark",
        )
    normalized = match.group(1).lower()
    return ParsedJudgment("VALID", normalized == "yes", normalized, None)


def deterministic_case_mapping(case_id: str, seed: int = 17) -> dict[str, str]:
    digest = hashlib.sha256(f"{seed}:{case_id}".encode("utf-8")).digest()
    baselines = ["EXT-B0", "EXT-B5"]
    if digest[0] & 1:
        baselines.reverse()
    return {"A": baselines[0], "B": baselines[1]}


def blinded_response_id(case_id: str, label: str, seed: int = 17) -> str:
    digest = hashlib.sha256(f"{seed}:{case_id}:{label}".encode("utf-8")).hexdigest()[:16]
    return f"response-{digest}"


def load_trials(raw_trial_directory: Path) -> list[dict[str, Any]]:
    files = sorted(raw_trial_directory.glob("*.json"))
    if len(files) != 40:
        raise ValueError(f"expected exactly 40 raw trial files, found {len(files)}")
    trials = [json.loads(path.read_text(encoding="utf-8")) for path in files]
    keys = [(row["case_id"], row["baseline_id"]) for row in trials]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate case/baseline trial")
    case_ids = sorted({row["case_id"] for row in trials})
    if len(case_ids) != 20:
        raise ValueError(f"expected exactly 20 cases, found {len(case_ids)}")
    for case_id in case_ids:
        present = {row["baseline_id"] for row in trials if row["case_id"] == case_id}
        if present != {"EXT-B0", "EXT-B5"}:
            raise ValueError(f"case {case_id} does not have exactly EXT-B0 and EXT-B5")
    trial_ids = [row["trial_id"] for row in trials]
    request_ids = [row["request_id"] for row in trials]
    if len(trial_ids) != len(set(trial_ids)):
        raise ValueError("duplicate trial IDs")
    if len(request_ids) != len(set(request_ids)):
        raise ValueError("duplicate request IDs")
    for row in trials:
        if row["baseline_id"] == "EXT-B0":
            if row.get("retrieved_items") or row.get("retrieval_tokens") or row.get("raw_prompt_or_reconstruction_fields", {}).get("history"):
                raise ValueError(f"EXT-B0 history leakage in {row['trial_id']}")
        if row["baseline_id"] == "EXT-B5" and not isinstance(row.get("retrieved_items"), list):
            raise ValueError(f"EXT-B5 retrieval trace missing in {row['trial_id']}")
    return trials


def verify_archive_registry(evidence_root: Path) -> dict[str, Any]:
    registry_path = evidence_root / "archive-registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    for item in registry.get("artifacts", []):
        path = evidence_root / item["path"]
        if not path.is_file():
            failures.append(f"missing:{item['path']}")
            continue
        digest = sha256_file(path)
        if digest != item["sha256"]:
            failures.append(f"hash:{item['path']}")
    if failures:
        raise ValueError("archive registry verification failed: " + ",".join(failures))
    return {
        "status": "PASS",
        "artifact_count": registry.get("artifact_count", len(registry.get("artifacts", []))),
        "registry_sha256": sha256_file(registry_path),
    }


def cohen_kappa(human: list[bool], judge: list[bool]) -> float | None:
    if len(human) != len(judge) or not human:
        return None
    n = len(human)
    observed = sum(a == b for a, b in zip(human, judge)) / n
    human_pos = sum(human) / n
    judge_pos = sum(judge) / n
    expected = human_pos * judge_pos + (1 - human_pos) * (1 - judge_pos)
    if math.isclose(expected, 1.0):
        return 1.0 if math.isclose(observed, 1.0) else 0.0
    return (observed - expected) / (1 - expected)


def safe_ratio(numerator: int | float, denominator: int | float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def calculate_calibration(
    audit_rows: Iterable[dict[str, Any]],
    judgment_by_case_baseline: dict[tuple[str, str], dict[str, Any]],
    *,
    full_output_count: int,
    full_invalid_count: int,
    thresholds: dict[str, float],
    blinding_verified: bool,
    old_evidence_preserved: bool,
    raw_outputs_preserved: bool,
) -> dict[str, Any]:
    audited = 0
    unscorable = 0
    valid = 0
    invalid = 0
    human_values: list[bool] = []
    judge_values: list[bool] = []
    tp = tn = fp = fn = 0
    abstention_total = abstention_correct = 0
    rows: list[dict[str, Any]] = []

    for row in audit_rows:
        audited += 1
        human_label = row.get("human_label")
        if human_label == "UNSCORABLE" or row.get("human_decision") is None:
            unscorable += 1
            rows.append({**row, "judge_status": "NOT_COMPARED", "outcome": "UNSCORABLE"})
            continue
        human_value = bool(row.get("human_decision")) if human_label is None else human_label == "CORRECT"
        key = (row["case_id"], row["baseline_id"])
        judgment = judgment_by_case_baseline.get(key)
        if judgment is None:
            raise ValueError(f"missing judge result for audited answer {key}")
        if judgment["status"] != "VALID":
            invalid += 1
            rows.append({**row, "judge_status": "INVALID", "outcome": "INVALID"})
            continue
        valid += 1
        judge_value = bool(judgment["correct"])
        human_values.append(human_value)
        judge_values.append(judge_value)
        if human_value and judge_value:
            tp += 1
            outcome = "TP"
        elif not human_value and not judge_value:
            tn += 1
            outcome = "TN"
        elif not human_value and judge_value:
            fp += 1
            outcome = "FP"
        else:
            fn += 1
            outcome = "FN"
        if row.get("is_abstention"):
            abstention_total += 1
            abstention_correct += int(human_value == judge_value)
        rows.append({**row, "judge_status": "VALID", "judge_decision": judge_value, "outcome": outcome})

    agreement = safe_ratio(sum(a == b for a, b in zip(human_values, judge_values)), valid)
    kappa = cohen_kappa(human_values, judge_values)
    invalid_rate = safe_ratio(full_invalid_count, full_output_count)
    pass_flags = {
        "raw_agreement": agreement is not None and agreement >= thresholds["raw_agreement_minimum"],
        "cohen_kappa": kappa is not None and kappa >= thresholds["cohen_kappa_minimum"],
        "invalid_output_rate": invalid_rate is not None and invalid_rate <= thresholds["invalid_output_rate_maximum"],
        "baseline_blinding": blinding_verified,
        "old_evidence_preserved": old_evidence_preserved,
        "raw_outputs_preserved": raw_outputs_preserved,
    }
    verdict = "PASS" if all(pass_flags.values()) else "FAIL"
    return {
        "schema_version": "longmemeval-evaluator-calibration-v2",
        "audit_status": "single-operator blinded calibration; not independent reproduction",
        "total_audited_answers": audited,
        "scorable_audited_answers": audited - unscorable,
        "unscorable_count": unscorable,
        "judge_valid_outputs_in_audit": valid,
        "judge_invalid_outputs_in_audit": invalid,
        "raw_agreement_valid_outputs": agreement,
        "cohens_kappa_valid_outputs": kappa,
        "confusion_valid_outputs": {
            "true_positive": tp,
            "true_negative": tn,
            "false_positive": fp,
            "false_negative": fn,
        },
        "positive_predictive_value": safe_ratio(tp, tp + fp),
        "negative_predictive_value": safe_ratio(tn, tn + fn),
        "sensitivity": safe_ratio(tp, tp + fn),
        "specificity": safe_ratio(tn, tn + fp),
        "abstention_accuracy_valid_outputs": safe_ratio(abstention_correct, abstention_total),
        "full_matrix_output_count": full_output_count,
        "full_matrix_invalid_output_count": full_invalid_count,
        "full_matrix_invalid_output_rate": invalid_rate,
        "thresholds": thresholds,
        "pass_flags": pass_flags,
        "calibration_verdict": verdict,
        "use_for_formal_correctness": "PERMITTED" if verdict == "PASS" else "PROHIBITED",
        "rows": rows,
    }


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    if total <= 0:
        return None, None
    p = successes / total
    denominator = 1 + z * z / total
    centre = p + z * z / (2 * total)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    return (centre - margin) / denominator, (centre + margin) / denominator


def exact_mcnemar_p(wins: int, losses: int) -> float | None:
    discordant = wins + losses
    if discordant == 0:
        return None
    smaller = min(wins, losses)
    cumulative = sum(math.comb(discordant, k) for k in range(smaller + 1)) / (2**discordant)
    return min(1.0, 2 * cumulative)


def summarize_formal_results(
    trials: list[dict[str, Any]],
    judgments: list[dict[str, Any]],
) -> dict[str, Any]:
    by_key = {(row["case_id"], row["baseline_id"]): row for row in judgments}
    by_baseline: dict[str, dict[str, Any]] = {}
    for baseline in ("EXT-B0", "EXT-B5"):
        rows = [row for row in judgments if row["baseline_id"] == baseline]
        valid_rows = [row for row in rows if row["status"] == "VALID"]
        correct = sum(bool(row["correct"]) for row in valid_rows)
        lower, upper = wilson_interval(correct, len(valid_rows))
        by_baseline[baseline] = {
            "total": len(rows),
            "valid": len(valid_rows),
            "invalid": len(rows) - len(valid_rows),
            "correct": correct,
            "accuracy": safe_ratio(correct, len(valid_rows)),
            "wilson_95": {"lower": lower, "upper": upper},
        }

    wins = losses = both_correct = both_incorrect = invalid_pairs = 0
    case_ids = sorted({row["case_id"] for row in trials})
    paired_rows: list[dict[str, Any]] = []
    for case_id in case_ids:
        b0 = by_key[(case_id, "EXT-B0")]
        b5 = by_key[(case_id, "EXT-B5")]
        if b0["status"] != "VALID" or b5["status"] != "VALID":
            invalid_pairs += 1
            outcome = "INVALID_PAIR"
        elif b0["correct"] and b5["correct"]:
            both_correct += 1
            outcome = "BOTH_CORRECT"
        elif not b0["correct"] and not b5["correct"]:
            both_incorrect += 1
            outcome = "BOTH_INCORRECT"
        elif not b0["correct"] and b5["correct"]:
            wins += 1
            outcome = "B5_WIN"
        else:
            losses += 1
            outcome = "B5_LOSS"
        paired_rows.append({"case_id": case_id, "outcome": outcome})

    p_value = exact_mcnemar_p(wins, losses)
    if p_value is not None and p_value < 0.05 and wins > losses:
        interpretation = "statistically supported improvement"
    elif p_value is not None and p_value < 0.05 and losses > wins:
        interpretation = "evidence of degradation"
    elif wins > losses:
        interpretation = "directional but inconclusive improvement"
    elif losses > wins:
        interpretation = "directional but inconclusive degradation"
    else:
        interpretation = "no detectable difference"

    trial_by_baseline = {
        baseline: [row for row in trials if row["baseline_id"] == baseline]
        for baseline in ("EXT-B0", "EXT-B5")
    }
    resource: dict[str, Any] = {}
    for baseline, rows in trial_by_baseline.items():
        latencies = sorted(float(row["latency_ms"]) for row in rows)
        resource[baseline] = {
            "answer_input_tokens": sum(int(row["input_tokens"]) for row in rows),
            "answer_output_tokens": sum(int(row["output_tokens"]) for row in rows),
            "answer_total_tokens": sum(int(row["total_tokens"]) for row in rows),
            "median_answer_latency_ms": (latencies[9] + latencies[10]) / 2,
            "recorded_output_storage_bytes": sum(int(row["storage_bytes"]) for row in rows),
            "estimated_monetary_cost_usd": sum(float(row.get("estimated_cost") or 0.0) for row in rows),
        }
    resource_difference = {
        key: resource["EXT-B5"][key] - resource["EXT-B0"][key]
        for key in resource["EXT-B0"]
    }
    correct_difference = by_baseline["EXT-B5"]["correct"] - by_baseline["EXT-B0"]["correct"]
    cost_per_additional_correct = (
        resource_difference["estimated_monetary_cost_usd"] / correct_difference
        if correct_difference > 0
        else None
    )
    return {
        "schema_version": "longmemeval-formal-summary-v2",
        "by_baseline": by_baseline,
        "absolute_accuracy_difference_b5_minus_b0": (
            by_baseline["EXT-B5"]["accuracy"] - by_baseline["EXT-B0"]["accuracy"]
            if by_baseline["EXT-B5"]["accuracy"] is not None and by_baseline["EXT-B0"]["accuracy"] is not None
            else None
        ),
        "paired": {
            "b5_wins": wins,
            "b5_losses": losses,
            "both_correct": both_correct,
            "both_incorrect": both_incorrect,
            "invalid_pairs": invalid_pairs,
            "discordant_pairs": wins + losses,
            "exact_mcnemar_two_sided_p": p_value,
            "effect_interpretation": interpretation,
            "power_warning": "The fixed sample has only 20 paired cases; low discordance implies very low power.",
            "rows": paired_rows,
        },
        "resource_comparison": {
            "by_baseline": resource,
            "difference_b5_minus_b0": resource_difference,
            "cost_per_additional_correct_answer_usd": cost_per_additional_correct,
            "cost_per_additional_correct_answer_display": (
                str(cost_per_additional_correct) if cost_per_additional_correct is not None else "UNDEFINED"
            ),
        },
    }
