from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

OFFICIAL_SOURCE_REPOSITORY = "https://github.com/xiaowu0162/LongMemEval"
OFFICIAL_SOURCE_COMMIT = "9e0b455f4ef0e2ab8f2e582289761153549043fc"
OFFICIAL_SOURCE_PATH = "src/evaluation/evaluate_qa.py"
OFFICIAL_SOURCE_BLOB_SHA = "4732f3772b04a2b9069121ade304e6320494abc2"
OFFICIAL_SOURCE_SHA256 = "ecce9c4c79dc89d99534ac17b383a5cbb5b9f0c69ee98adaf0684742e3d95251"
OFFICIAL_LICENSE = "MIT"
OFFICIAL_OPENAI_MODEL = "gpt-4o-2024-08-06"
OFFICIAL_LOCAL_MODEL = "meta-llama/Meta-Llama-3.1-70B-Instruct"
SEED = 17
EXPECTED_CASE_ID_SHA256 = "519b4db13813b60ad6a49cce919543b0639524a98bd1b0d1615c53e62cf8cc7e"

_GENERIC_TEMPLATE = (
    "I will give you a question, a correct answer, and a response from a model. "
    "Please answer yes if the response contains the correct answer. Otherwise, answer no. "
    "If the response is equivalent to the correct answer or contains all the intermediate steps "
    "to get the correct answer, you should also answer yes. If the response only contains a subset "
    "of the information required by the answer, answer no. \n\nQuestion: {question}\n\n"
    "Correct Answer: {answer}\n\nModel Response: {response}\n\n"
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
    "model's response is still correct. \n\nQuestion: {question}\n\nCorrect Answer: {answer}\n\n"
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

# The semantic rubric remains the official yes/no rubric. The port changes only the
# response transport contract so malformed output can be retained as INVALID.
_STRUCTURED_OUTPUT_SUFFIX = (
    '\n\nOutput contract: return exactly one JSON object, either '
    '{"label":"CORRECT"} for yes or {"label":"INCORRECT"} for no. '
    "Do not add any other key or text."
)

OFFICIAL_PROMPT_TEMPLATES: dict[str, str] = {
    "generic": _GENERIC_TEMPLATE,
    "temporal-reasoning": _TEMPORAL_TEMPLATE,
    "knowledge-update": _KNOWLEDGE_UPDATE_TEMPLATE,
    "single-session-preference": _PREFERENCE_TEMPLATE,
    "abstention": _ABSTENTION_TEMPLATE,
}

FORBIDDEN_BLINDING_TERMS = (
    "ext-b0",
    "ext-b5",
    "no-memory",
    "retrieval",
    "control",
    "treatment",
    "baseline",
    "bm25",
    "history budget",
    "token cost",
    "latency",
)


@dataclass(frozen=True)
class ParsedJudgment:
    status: str
    label: str | None
    correct: bool | None
    error: str | None


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def case_ids_sha256(case_ids: Iterable[str]) -> str:
    return sha256_text(canonical_json(sorted(case_ids)))


def official_prompt_bundle() -> dict[str, Any]:
    return {
        "source_commit": OFFICIAL_SOURCE_COMMIT,
        "source_path": OFFICIAL_SOURCE_PATH,
        "templates": OFFICIAL_PROMPT_TEMPLATES,
        "structured_output_suffix": _STRUCTURED_OUTPUT_SUFFIX,
    }


def prompt_bundle_sha256() -> str:
    return sha256_text(canonical_json(official_prompt_bundle()))


def parser_sha256() -> str:
    return sha256_text(inspect.getsource(parse_strict_judgment))


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


def build_faithful_port_prompt(
    question_type: str,
    question: str,
    reference_answer: str,
    candidate_answer: str,
    *,
    abstention: bool,
) -> str:
    return build_official_prompt(
        question_type,
        question,
        reference_answer,
        candidate_answer,
        abstention=abstention,
    ) + _STRUCTURED_OUTPUT_SUFFIX


def parse_strict_judgment(
    raw_output: str | None,
    *,
    provider_error: str | None = None,
    timed_out: bool = False,
    truncated: bool = False,
) -> ParsedJudgment:
    if provider_error:
        return ParsedJudgment("INVALID", None, None, f"provider_error:{provider_error}")
    if timed_out:
        return ParsedJudgment("INVALID", None, None, "timeout")
    if truncated:
        return ParsedJudgment("INVALID", None, None, "truncated_output")
    if not isinstance(raw_output, str) or not raw_output.strip():
        return ParsedJudgment("INVALID", None, None, "empty_or_non_text_output")
    try:
        payload = json.loads(raw_output)
    except (TypeError, json.JSONDecodeError) as exc:
        return ParsedJudgment("INVALID", None, None, f"invalid_json:{exc.__class__.__name__}")
    if not isinstance(payload, dict):
        return ParsedJudgment("INVALID", None, None, "schema_not_object")
    if set(payload) != {"label"}:
        return ParsedJudgment("INVALID", None, None, "schema_keys_must_equal_label")
    label = payload.get("label")
    if label not in {"CORRECT", "INCORRECT"}:
        return ParsedJudgment("INVALID", None, None, "label_not_in_enum")
    return ParsedJudgment(label, label, label == "CORRECT", None)


def anonymous_response_id(trial_id: str, seed: int = SEED) -> str:
    return "response-" + sha256_text(f"{seed}:{trial_id}")[:20]


def load_raw_trials(evidence_root: Path, split_manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_dir = evidence_root / "raw-trials"
    files = sorted(raw_dir.glob("*.json"))
    if len(files) != 40:
        raise ValueError(f"expected exactly 40 raw trial files, found {len(files)}")
    trials: list[dict[str, Any]] = []
    for path in files:
        if path.stat().st_size == 0:
            raise ValueError(f"empty raw trial file: {path.name}")
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid raw trial JSON: {path.name}") from exc
        row = dict(row)
        row["_path"] = path
        trials.append(row)

    expected_cases = set(split_manifest["case_ids"])
    if len(expected_cases) != 20:
        raise ValueError("split manifest must contain exactly 20 case IDs")
    if case_ids_sha256(expected_cases) != split_manifest["case_ids_sha256"]:
        raise ValueError("split manifest case-ID hash mismatch")
    if split_manifest["case_ids_sha256"] != EXPECTED_CASE_ID_SHA256:
        raise ValueError("unexpected frozen case-ID hash")

    trial_ids = [row.get("trial_id") for row in trials]
    request_ids = [row.get("request_id") for row in trials]
    if None in trial_ids or len(set(trial_ids)) != 40:
        raise ValueError("trial IDs are missing or not unique")
    if None in request_ids or len(set(request_ids)) != 40:
        raise ValueError("request IDs are missing or not unique")

    seen_pairs: set[tuple[str, str]] = set()
    for row in trials:
        case_id = row.get("case_id")
        baseline_id = row.get("baseline_id")
        if case_id not in expected_cases:
            raise ValueError(f"case outside frozen manifest: {case_id}")
        if baseline_id not in {"EXT-B0", "EXT-B5"}:
            raise ValueError(f"unexpected baseline: {baseline_id}")
        pair = (case_id, baseline_id)
        if pair in seen_pairs:
            raise ValueError(f"duplicate case/baseline pair: {pair}")
        seen_pairs.add(pair)
        if row.get("status") != "completed" or row.get("error_type") or row.get("error_message"):
            raise ValueError(f"trial is not a clean completed answer: {row.get('trial_id')}")
        if not isinstance(row.get("parsed_answer"), str) or not row["parsed_answer"].strip():
            raise ValueError(f"missing answer text: {row.get('trial_id')}")
        prompt_fields = row.get("raw_prompt_or_reconstruction_fields") or {}
        if baseline_id == "EXT-B0":
            if row.get("retrieved_items") not in ([], None):
                raise ValueError(f"EXT-B0 retrieved items present: {row['trial_id']}")
            if row.get("retrieval_tokens") not in (0, None):
                raise ValueError(f"EXT-B0 retrieval tokens present: {row['trial_id']}")
            if prompt_fields.get("history") not in ("", None):
                raise ValueError(f"EXT-B0 cross-session history present: {row['trial_id']}")
        else:
            items = row.get("retrieved_items")
            if not isinstance(items, list) or not items:
                raise ValueError(f"EXT-B5 retrieval trace missing: {row['trial_id']}")
            scores = row.get("retrieval_scores") or []
            timestamps = row.get("retrieval_timestamps") or []
            if scores and len(scores) != len(items):
                raise ValueError(f"EXT-B5 retrieval score length mismatch: {row['trial_id']}")
            if timestamps and len(timestamps) != len(items):
                raise ValueError(f"EXT-B5 retrieval timestamp length mismatch: {row['trial_id']}")

    expected_pairs = {(case_id, baseline) for case_id in expected_cases for baseline in ("EXT-B0", "EXT-B5")}
    if seen_pairs != expected_pairs:
        raise ValueError("case/baseline matrix is incomplete")
    return sorted(trials, key=lambda row: (row["case_id"], row["baseline_id"], row["trial_id"]))


def build_immutable_answer_manifest(trials: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for row in trials:
        path = Path(row["_path"])
        rows.append(
            {
                "case_id": row["case_id"],
                "baseline_id": row["baseline_id"],
                "trial_id": row["trial_id"],
                "request_id": row["request_id"],
                "answer_sha256": sha256_text(row["parsed_answer"]),
                "trial_file_sha256": sha256_file(path),
                "trial_file": path.name,
            }
        )
    ordered_payload = [
        {key: item[key] for key in ("case_id", "baseline_id", "trial_id", "request_id", "answer_sha256")}
        for item in rows
    ]
    unordered_payload = sorted(item["answer_sha256"] for item in rows)
    raw_trial_payload = sorted(
        (
            {"trial_file": item["trial_file"], "trial_file_sha256": item["trial_file_sha256"]}
            for item in rows
        ),
        key=lambda item: (item["trial_file"], item["trial_file_sha256"]),
    )
    return {
        "schema_version": "longmemeval-immutable-answer-manifest-v3",
        "sorting_rule": "case_id ASC, baseline_id ASC, trial_id ASC",
        "answer_text_field": "parsed_answer",
        "trial_count": len(rows),
        "rows": rows,
        "ordered_answer_set_sha256": sha256_text(canonical_json(ordered_payload)),
        "unordered_answer_multiset_sha256": sha256_text(canonical_json(unordered_payload)),
        "raw_trial_set_sha256": sha256_text(canonical_json(raw_trial_payload)),
    }


def verify_archive_registry(evidence_root: Path) -> dict[str, Any]:
    registry_path = evidence_root / "archive-registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    artifacts = registry.get("artifacts", [])
    if registry.get("artifact_count") != 59 or len(artifacts) != 59:
        raise ValueError("archive registry must contain exactly 59 preserved artifacts")
    failures: list[str] = []
    for item in artifacts:
        path = evidence_root / item["path"]
        if not path.is_file():
            failures.append(f"missing:{item['path']}")
            continue
        if path.stat().st_size != item["size_bytes"]:
            failures.append(f"size:{item['path']}")
        if sha256_file(path) != item["sha256"]:
            failures.append(f"hash:{item['path']}")
    if failures:
        raise ValueError("archive registry verification failed: " + ",".join(failures))
    return {
        "status": "PASS",
        "artifact_count": 59,
        "registered_artifact_sha256_checks": 59,
    }


def build_blinded_inputs(
    trials: Sequence[Mapping[str, Any]],
    split_manifest: Mapping[str, Any],
    *,
    seed: int = SEED,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    split_by_case = {row["case_id"]: row for row in split_manifest["records"]}
    blinded: list[dict[str, Any]] = []
    key: list[dict[str, Any]] = []
    answer_originated_leakage: list[dict[str, str]] = []
    for trial in sorted(trials, key=lambda row: sha256_text(f"{seed}:{row['trial_id']}")):
        split_row = split_by_case[trial["case_id"]]
        response_id = anonymous_response_id(trial["trial_id"], seed)
        question = str(trial["raw_prompt_or_reconstruction_fields"]["question"])
        reference_answer = str(trial["reference_answer"])
        candidate_answer = str(trial["parsed_answer"])
        prompt = build_faithful_port_prompt(
            trial["question_type"],
            question,
            reference_answer,
            candidate_answer,
            abstention=bool(split_row["is_abstention"]),
        )
        record = {
            "schema_version": "longmemeval-faithful-port-blinded-input-v3",
            "anonymous_response_id": response_id,
            "question": question,
            "reference_answer": reference_answer,
            "question_type": trial["question_type"],
            "is_abstention": bool(split_row["is_abstention"]),
            "model_response": candidate_answer,
            "prompt": prompt,
        }
        for field_name in ("question", "reference_answer", "model_response"):
            value = str(record[field_name]).lower()
            for term in FORBIDDEN_BLINDING_TERMS:
                if term in value:
                    answer_originated_leakage.append(
                        {"anonymous_response_id": response_id, "field": field_name, "term": term}
                    )
        blinded.append(record)
        key.append(
            {
                "anonymous_response_id": response_id,
                "case_id": trial["case_id"],
                "baseline_id": trial["baseline_id"],
                "trial_id": trial["trial_id"],
                "request_id": trial["request_id"],
                "answer_sha256": sha256_text(candidate_answer),
            }
        )
    if len({row["anonymous_response_id"] for row in blinded}) != len(blinded):
        raise ValueError("anonymous response IDs are not unique")
    return blinded, key, answer_originated_leakage


def verify_blinded_records(
    blinded: Sequence[Mapping[str, Any]],
    key: Sequence[Mapping[str, Any]],
    *,
    allowed_answer_originated_leakage: Sequence[Mapping[str, str]] = (),
) -> None:
    allowed = {
        (row["anonymous_response_id"], row["field"], row["term"])
        for row in allowed_answer_originated_leakage
    }
    forbidden_keys = {"case_id", "baseline_id", "trial_id", "request_id", "provider"}
    if len(blinded) != 40 or len(key) != 40:
        raise ValueError("blinded inputs and key must each contain 40 rows")
    key_ids = {row["anonymous_response_id"] for row in key}
    for row in blinded:
        if forbidden_keys.intersection(row):
            raise ValueError("identity-bearing key present in blinded input")
        response_id = row["anonymous_response_id"]
        if response_id not in key_ids:
            raise ValueError("blinded input missing from unblinding key")
        for field_name in ("question", "reference_answer", "model_response"):
            value = str(row[field_name]).lower()
            for term in FORBIDDEN_BLINDING_TERMS:
                if term in value and (response_id, field_name, term) not in allowed:
                    raise ValueError(f"unrecorded answer-originated identity leakage: {response_id}:{term}")
        identity_free = {
            key_name: value
            for key_name, value in row.items()
            if key_name not in {"question", "reference_answer", "model_response", "prompt"}
        }
        serialized = canonical_json(identity_free).lower()
        for term in FORBIDDEN_BLINDING_TERMS:
            if term in serialized:
                raise ValueError(f"structural identity leakage: {response_id}:{term}")


def jsonl_dump(rows: Sequence[Mapping[str, Any]]) -> str:
    return "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def parsed_judgment_to_dict(judgment: ParsedJudgment) -> dict[str, Any]:
    return asdict(judgment)
