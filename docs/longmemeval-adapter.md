# LongMemEval Adapter Notes

Source review date: 2026-07-31

## Official source inspected

```text
Repository: xiaowu0162/LongMemEval
Source commit used for schema review: 9e0b455f4ef0e2ab8f2e582289761153549043fc
Official evaluation file: src/evaluation/evaluate_qa.py
```

The official schema defines:

- `question_id`
- `question_type`
- `question`
- `answer`
- `question_date`
- `haystack_session_ids`
- `haystack_dates`
- `haystack_sessions`
- `answer_session_ids`

History sessions contain `user` and `assistant` turns. Evidence turns may include `has_answer: true`. Official hypotheses are JSONL records containing `question_id` and `hypothesis`.

## Implemented scope

`src/personal_state_engine/longmemeval.py` provides:

- strict JSON and JSONL loading;
- supported question-type validation;
- aligned session ID, date and session-content validation;
- duplicate question and session detection;
- turn-role and evidence-label validation;
- answer-session membership validation;
- immutable parsed examples;
- chronological JSON context rendering;
- recent-session and user-only rendering controls;
- hypothesis JSONL read and write support.

## Explicit non-claims

- The official dataset has not been downloaded into this environment.
- No dataset hash has been recorded.
- The official evaluator has not been executed.
- No model response has been generated.
- No LongMemEval score exists for this repository.
- The adapter is not an official reproduction of the benchmark authors' memory systems.

## Evaluator governance

The official QA evaluator uses an LLM judge and task-specific yes/no prompts. This repository must not silently replace it with a different scorer and retain direct comparability. Before formal use:

1. pin the official evaluator source revision;
2. pin the judge model revision and request date;
3. save the exact judge prompt or its hash;
4. retain raw judge outputs;
5. define parse-failure and retry policy;
6. calibrate a sample against human labels;
7. label any deterministic substitute as a separate exploratory metric.

## Next executable step

Acquire `longmemeval_s_cleaned.json` through a working network path, verify licensing, record its cryptographic hash, run this adapter over the full file and compare counts and question-type distributions with the official release documentation.
