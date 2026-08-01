# Research Progress

Assessment date: 2026-08-01 09:25 +08:00

## Executive status

```text
Research verdict: BLOCKED
Evidence-weighted completion: 24%
Highest evidence level: E3 — real-model external development evidence
Algorithm parity demonstrated: NO
PR #2: OPEN / DRAFT / NOT MERGED
```

The fixed 20-case LongMemEval-S development matrix completed at the raw-evidence level. EXT-B0 and EXT-B5 each completed 20 real-model trials with no model errors or timeouts, but the preregistered semantic evaluator failed calibration. As a result, the current evidence supports execution, retrieval and resource claims only; it does not support answer-quality comparison.

## A. GitHub state

```text
Research branch: research/personal-state-engine-v0
Evidence commit: 333f1019470facd35775d7f2ed314b9191db12dd
PR: #2
PR state: OPEN / DRAFT
Merge status: not merged
Evidence workflow run: 30677673098
Formal matrix workflow run: 30676516785
Formal matrix job: 91304822403
CI run: 30676516773 — SUCCESS
Tests: 109 on Python 3.11 / 3.12 / 3.13
Blocker issue: #6
```

No tag or GitHub Release was created.

## B. Protocol and data

```text
Activated protocol: experiments/protocols/longmemeval-development-matrix-v2.json
Original protocol: experiments/protocols/longmemeval-development-matrix-v1.json
Frozen split: experiments/splits/longmemeval-development-matrix-v1.json
Case count: 20
Abstention cases: 4
Case-ID SHA-256: 519b4db13813b60ad6a49cce919543b0639524a98bd1b0d1615c53e62cf8cc7e
Manifest self hash: 9556458b9ae684cd7906f3182b457ea69fe776436ea78cfb2ce9e42ac1745a1b
History isolation: PASS
Sealed-final accessed: false
```

Question-type distribution:

| Type | Cases |
|---|---:|
| knowledge-update | 3 |
| multi-session | 4 |
| single-session-assistant | 3 |
| single-session-preference | 2 |
| single-session-user | 3 |
| temporal-reasoning | 5 |

Dataset:

```text
Name: LongMemEval-S cleaned
Revision: 98d7416c24c778c2fee6e6f3006e7a073259d48f
SHA-256: d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442
Size: 277383467 bytes
Payload committed to Git: no
```

Protocol v2 preserved the 20 case IDs and model from v1. It was versioned before the successful run because three prior infrastructure attempts ended with runner shutdown signals before producing a complete comparison. The evidence showed that the declared history budget was not enforced. V2 fixed deterministic 1,024 lexical-token truncation and bounded the model subprocess lifetime per formal case; no observed answer-quality result was used to choose the change.

## C. Model and runtime

```text
Model: onnx-community/Qwen2.5-0.5B-Instruct
Model revision: 956050e4c6ce7c647091e15311218f80d662559f
Tokenizer revision: 956050e4c6ce7c647091e15311218f80d662559f
Quantization: q4
Runtime: @huggingface/transformers 4.2.0
Generation: temperature 0, no sampling, max 96 new tokens, seed 17
Hardware: GitHub-hosted ubuntu-24.04 CPU runner
License: Apache-2.0
Capability screening: 2 non-overlapping development cases, PASS
```

The screening proves executability only. It does not prove that the 0.5B model eliminated floor effects or is competitive with published LongMemEval systems.

Security limitation: `npm audit` retains four high-severity findings with no automatic fix in the captured graph. Execution is restricted to ephemeral isolated research runners; no security or production-readiness claim is allowed.

## D. Evaluator calibration

```text
Evaluator: qwen2.5-0.5b-semantic-judge-v1
Judge revision: 956050e4c6ce7c647091e15311218f80d662559f
Baseline identity hidden: yes
Structured output required: yes
Human audit: 10 cases / 20 answers
Audit type: single-operator blinded audit; not independent
```

| Calibration metric | Observed | Required | Result |
|---|---:|---:|---|
| Full-matrix invalid output rate | 27.5% | <= 5% | FAIL |
| Valid-output raw agreement | 15.4% | >= 80% | FAIL |
| Cohen's kappa | 0.00 | >= 0.60 | FAIL |
| False positives | 11 | — | severe bias |
| False negatives | 0 | — | — |
| True negatives | 0 | — | no negative discrimination |

```text
Calibration verdict: FAIL
Formal correctness use: PROHIBITED
```

The valid judge outputs were effectively positive-only. Issue #6 records the blocker and acceptance criteria for evaluator replacement.

## E. Experiment execution

```text
Run ID: development-matrix-30676516785-attempt-1
Formal cases: 20
Baselines: EXT-B0 / EXT-B5
Trials: 40
Completed: 40
Model errors: 0
Timeouts: 0
Retries inside successful run: 0
Raw-to-summary tie-out: PASS
Artifact-registry hashes: PASS
Unique trial IDs: PASS
Unique request IDs: PASS
EXT-B0 history exclusion: PASS
EXT-B5 retrieval trace: PASS
Sealed-final access: false
```

Durable evidence:

```text
results/external/longmemeval-development-matrix-30676516785/
```

The directory contains 40 immutable raw trial JSON files, original and archival registries, environment/model manifests, dependency audit, progress logs, processed summary, blinded audit, calibration report, gate assessment, provenance and research verdict. Dataset payload and model weights are excluded.

## F. Results

### Valid descriptive results

| Metric | EXT-B0 | EXT-B5 | Difference |
|---|---:|---:|---:|
| Cases | 20 | 20 | 0 |
| Completed | 20 | 20 | 0 |
| Errors | 0 | 0 | 0 |
| Timeouts | 0 | 0 | 0 |
| Answer input tokens | 1,866 | 30,680 | +28,814 |
| Answer output tokens | 1,871 | 1,901 | +30 |
| Answer + judge combined tokens | 121,297 | 150,451 | +29,154 |
| Median answer latency | 2,009 ms | 14,222 ms | +12,213 ms |
| Recorded output storage | 24,199 bytes | 53,574 bytes | +29,375 bytes |
| API monetary charge | USD 0 | USD 0 | USD 0 |

Retrieval diagnostics:

```text
Answer-bearing session recall@k: 18/20 = 0.90
B5 history budget: 1024 lexical tokens
B5 cases truncated: 20/20
has_answer used for ranking: false
```

### Invalidated correctness results

The processed summary contains provisional judge-derived correctness fields, but the evaluator failed calibration. These fields must not be reported as formal accuracy, paired wins/losses, confidence intervals, McNemar tests, effect sizes, or cost per additional correct answer.

```text
Formal B0 accuracy: NOT AVAILABLE
Formal B5 accuracy: NOT AVAILABLE
Formal difference: NOT AVAILABLE
Formal paired statistical test: NOT AVAILABLE
Cost per additional correct answer: UNDEFINED
```

## G. Evidence verdict

Highest evidence level: `E3`.

Supported:

1. The pinned dataset and unchanged frozen 20-case subset executed under protocol v2.
2. Both baselines completed all 20 trials with complete raw evidence.
3. Evidence integrity, B0 isolation, B5 traceability and sealed-final non-access passed.
4. BM25 retrieval and resource-overhead diagnostics are available for this fixed configuration.

Not supported:

1. EXT-B5 improves, matches or underperforms EXT-B0 on answer correctness.
2. The 0.5B model avoids floor effects.
3. The evaluator is reliable.
4. Algorithm parity, superiority, equivalence, non-inferiority, generalization, security or production readiness.

## H. Gate assessment

| Gate | Previous | Current | Evidence | Missing |
|---|---:|---:|---|---|
| A — Repository, sources and licensing | 9% | 10% | Exact source/model/runtime revisions and licenses | None material for current inputs |
| B — Experiment infrastructure | 9% | 10% | Frozen protocol/split, immutable trials, budget enforcement, durable archive and reconstruction | None material for current contract |
| C — Basic external baselines | 2% | 4% | 20 paired cases and complete resource/retrieval evidence | Calibrated evaluator and valid correctness analysis |
| D — Strong baseline | 0% | 0% | None | Faithful strong baseline |
| E — PSE candidate | 0% | 0% | None | Blocked until baselines stabilize |
| F — Sealed parity test | 0% | 0% | Sealed-final remained untouched | Preregistered sealed execution |
| G — Independent reproduction | 0% | 0% | None | Independent operator/environment |

```text
Previous completion: 20%
Current completion: 24%
Remaining distance: 76%
Active evidence cap: 45%
```

## I. Active blockers

### Evaluator calibration

```text
Status: BLOCKED
Cause: invalid and severely false-positive semantic judge
Evidence: evaluator-calibration.json and Issue #6
Impact: no formal answer-quality or paired statistical conclusion
Next action: integrate official evaluator or a stronger fixed blinded judge and rescore unchanged raw outputs
Acceptance: agreement >= 0.80, kappa >= 0.60, invalid rate <= 5%
```

### Runtime dependency security

```text
Status: OPEN BLOCKER
Cause: four high-severity findings in the pinned JavaScript inference dependency graph
Evidence: npm-audit.json
Impact: isolated research execution only; no secure/production claim
Next action: migrate to a fixed graph without high/critical findings or document a narrower verified isolation boundary
Acceptance: high/critical count zero, or explicit approved research-only isolation with no production path
```

## J. Final research verdict

```text
BLOCKED
```

The raw development matrix succeeded as an engineering and evidence exercise. The research question remains unanswered because the evaluator did not meet the preregistered reliability threshold.

## K. Next highest-value actions

1. Replace and calibrate the semantic evaluator, then rescore the unchanged 40 raw answers.
2. After calibration passes, regenerate formal paired statistics and cost-per-additional-correct analysis without rerunning or reselecting cases unless the answer-model protocol itself changes.
3. Only after the B0/B5 matrix is valid, decide whether to add EXT-B1–EXT-B6; do not begin PSE-Min or sealed-final yet.

## Publication status

- PR #2 remains Draft.
- Do not merge.
- Do not tag or create a GitHub Release.
- Do not claim parity, superiority, validation, security, production readiness or state of the art.
