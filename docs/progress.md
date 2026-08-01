# Research Progress

Assessment date: 2026-08-01 14:58 +08:00

## Executive status

```text
Research verdict: INCONCLUSIVE
Evidence-weighted completion: 30%
Highest evidence level: E3 — calibrated real-model external development evidence
Algorithm parity demonstrated: NO
PR #2: OPEN / DRAFT / NOT MERGED
```

The fixed 20-case LongMemEval-S EXT-B0/EXT-B5 development matrix has now been rescored with evaluator v2. The evaluator passed the preregistered calibration thresholds, so formal development-set correctness statistics are permitted. EXT-B5 scored higher than EXT-B0, but the sample contains only four discordant pairs and the exact paired test is not significant. The result is directional but inconclusive, not evidence of parity or superiority.

## A. GitHub state

```text
Research branch: research/personal-state-engine-v0
Development evidence commit: 333f1019470facd35775d7f2ed314b9191db12dd
Evaluator v2 evidence commit: 0fb95bd7d6a01f1553cfab7a28a4ca2c84bd7948
Formal matrix workflow run: 30676516785
Evaluator v2 workflow run: 30688327468
Evaluator v2 job: 91338369889
PR: #2
PR state: OPEN / DRAFT
Merge status: not merged
Issue #6: evaluator blocker resolved; pending final closeout update
Tag: none
Release: none
```

Evaluator workflow run `30688327468` passed source-evidence verification, evaluator execution, calibration, formal rescoring, evidence-contract verification, benchmark-lock refresh, 118 automated tests, complete engineering checks, evidence commit and artifact upload.

## B. Fixed protocol and evidence

```text
Development protocol: experiments/protocols/longmemeval-development-matrix-v2.json
Frozen split: experiments/splits/longmemeval-development-matrix-v1.json
Case count: 20
Abstention cases: 4
Case-ID SHA-256: 519b4db13813b60ad6a49cce919543b0639524a98bd1b0d1615c53e62cf8cc7e
Answer trials: 40
Answer-model rerun: false
Case IDs changed: false
Sealed-final accessed: false
```

Dataset and answer model:

```text
Dataset: LongMemEval-S cleaned
Dataset revision: 98d7416c24c778c2fee6e6f3006e7a073259d48f
Dataset SHA-256: d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442
Answer model: onnx-community/Qwen2.5-0.5B-Instruct
Answer-model revision: 956050e4c6ce7c647091e15311218f80d662559f
Runtime: @huggingface/transformers 4.2.0, q4
```

The 40 original answer records remain under:

```text
results/external/longmemeval-development-matrix-30676516785/
```

The evaluator v2 evidence is under:

```text
results/external/longmemeval-evaluator-v2/
```

The v2 archive contains blinded inputs, a deterministic unblinding key, 54 raw judge outputs, parsed judgments, the original blinded human audit, calibration metrics, formal rescoring, paired analysis, source/runtime manifests and a 74-file artifact registry. The old failed v1 evaluator evidence remains unchanged.

## C. Evaluator source and selection

Priority investigation found the official LongMemEval evaluator in:

```text
Repository: https://github.com/xiaowu0162/LongMemEval
Commit: 9e0b455f4ef0e2ab8f2e582289761153549043fc
Path: src/evaluation/evaluate_qa.py
License: MIT
Official judge: gpt-4o-2024-08-06
Official runtime: openai-python 1.35.1
```

No confirmed usable OpenAI API credential was available before inference, and a CPU runner cannot reasonably reproduce the official local 70B path. The selection policy therefore activated the exact-pinned local fallback before any formal result was observed:

```text
Evaluator ID: longmemeval-official-prompt-priority-v2
Source type: custom-calibrated using official prompt semantics
Provider: local-fallback
Judge: onnx-community/Llama-3.2-3B-Instruct-ONNX
Judge revision: cab364e7d0e1de7aa09e3abc932be92361c5b55f
Judge license: llama3.2
Runtime: @huggingface/transformers 4.2.0
Quantization: q4
Temperature: 0
Sampling: false
Seed: 17
Max output tokens: 10
Prompt SHA-256: be177cbb0e82bf279ad8c24e8d553ef80222464dd51c39ef7bea7231623d28e6
Parser SHA-256: 975e659fd3a109a40c8316fc532bf010a0dbf71208bcbb97978146e9d917f0e2
```

The parser accepts only an exact case-insensitive `yes` or `no`, with an optional final period or exclamation mark. Any other output is retained as `INVALID`; invalid outputs are not silently converted to correct or incorrect.

## D. Separate evaluator unit corpus

The 14-case evaluator-development corpus was separate from the 40 fixed formal answers.

```text
Cases: 14
Valid outputs: 14
Invalid outputs: 0
Correct classifications: 13
Accuracy on valid outputs: 92.86%
```

The one miss was a response containing the correct core answer plus a materially wrong added fact. This remains a known evaluator limitation even though the formal blinded calibration passed.

## E. Blinded calibration

```text
Audit scope: 10 cases / 20 answers
Audit status: single-operator blinded calibration; not independent reproduction
Baseline identity hidden: true
Scorable answers: 20
Unscorable answers: 0
Judge valid outputs: 20
Judge invalid outputs: 0
```

| Calibration metric | Observed | Required | Result |
|---|---:|---:|---|
| Raw agreement | 95.0% | >= 80% | PASS |
| Cohen's kappa | 0.7727 | >= 0.60 | PASS |
| Full-matrix invalid-output rate | 0.0% | <= 5% | PASS |
| Abstention accuracy on valid audit outputs | 100% | — | — |
| Sensitivity | 66.7% | — | limited positive recall |
| Specificity | 100% | — | — |
| Positive predictive value | 100% | — | — |
| Negative predictive value | 94.4% | — | — |

Confusion matrix:

```text
TP = 2
TN = 17
FP = 0
FN = 1
```

```text
Calibration verdict: PASS
Formal correctness use: PERMITTED
```

The calibration meets every fixed gate. However, it contains only three human-positive examples and is not an independent second-operator replication. This limits confidence in sensitivity and generalization.

## F. Formal rescoring

| Metric | EXT-B0 | EXT-B5 | Difference |
|---|---:|---:|---:|
| Correct | 2 | 4 | +2 |
| Valid | 20 | 20 | 0 |
| Invalid | 0 | 0 | 0 |
| Accuracy | 10.0% | 20.0% | +10.0 percentage points |
| Wilson 95% interval | 2.8%–30.1% | 8.1%–41.6% | wide and overlapping |

Paired result:

```text
B5 wins: 3
B5 losses: 1
Both correct: 1
Both incorrect: 15
Discordant pairs: 4
Exact McNemar two-sided p-value: 0.625
Effect interpretation: directional but inconclusive improvement
```

The small number of discordant pairs gives very low statistical power. `p = 0.625` is not evidence of equivalence, non-inferiority or no effect. It means the fixed development sample does not establish a reliable difference.

## G. Resource comparison

The resource values below come from the original answer trials, not the evaluator inference.

| Metric | EXT-B0 | EXT-B5 | B5 minus B0 |
|---|---:|---:|---:|
| Answer input tokens | 1,866 | 30,680 | +28,814 |
| Answer output tokens | 605 | 977 | +372 |
| Answer total tokens | 2,471 | 31,657 | +29,186 |
| Median answer latency | 2,009 ms | 14,222 ms | +12,213 ms |
| Recorded output storage | 22,785 bytes | 157,328 bytes | +134,543 bytes |
| Recorded monetary charge | USD 0 | USD 0 | USD 0 |

B5 produced two additional correct answers in this fixed sample. The recorded monetary cost per additional correct answer is USD 0 because the answer runs used local inference and recorded no API charge. This is not evidence that B5 is economically free: it required substantially more tokens, latency and storage.

## H. Evidence integrity

```text
Original raw trials present: 40/40
Original archive artifacts verified: 59/59
Evaluator v2 artifacts verified: 74/74
Raw judge outputs preserved: yes
Formal parsed judgments: 40
Unit parsed judgments: 14
Baseline blinding: PASS
Raw-to-summary reconstruction: PASS
Original v1 failure evidence preserved: PASS
Dataset payload committed: no
Model weights committed: no
Sealed-final accessed: false
```

The evaluator workflow used a temporary compatibility symlink tree only to let the original evidence verifier resolve its archived registry paths. The symlink tree was deleted immediately after verification; no evidence bytes were altered.

## I. Gate assessment

| Gate | Previous | Current | Evidence | Missing |
|---|---:|---:|---|---|
| A — Repository, sources and licensing | 10% | 10% | Exact dataset, answer-model, evaluator-source and runtime revisions | None material for current inputs |
| B — Experiment infrastructure | 10% | 10% | Frozen protocol, immutable answers, blinded evaluator, reconstruction and durable archives | None material for current contract |
| C — Basic external baselines | 4% | 10% | Calibrated 20-case B0/B5 formal comparison and paired analysis | Larger sample, stronger answer model and additional baselines |
| D — Strong baseline reproduction | 0% | 0% | None | Faithful published strong baseline |
| E — PSE candidate | 0% | 0% | None | External PSE-Min implementation and ablation |
| F — Sealed parity test | 0% | 0% | Sealed-final remained untouched | Activated preregistration and sealed execution |
| G — Independent reproduction | 0% | 0% | None | Independent operator and environment |

```text
Previous completion: 24%
Current completion: 30%
Remaining distance: 70%
Active evidence cap: 45%
```

Completion increased only for the now-valid development comparison. It did not increase for code volume, workflow count or documentation.

## J. Active blockers

### Statistical and model adequacy

```text
Cause: only 20 paired cases, four discordant pairs and a 0.5B answer model with low absolute accuracy
Evidence: B0 2/20, B5 4/20, exact McNemar p=0.625
Impact: no supported efficacy or parity conclusion
Next action: preregister a larger development comparison with a more capable fixed answer model before any sealed test
Acceptance: adequate power or explicitly justified sample, floor-effect screening, calibrated evaluator and preserved pairing
```

### Strong-baseline gap

```text
Cause: no faithful published strong memory baseline has been reproduced
Impact: evidence cap remains 45%; parity cannot be assessed
Next action: select and reproduce one pinned strong baseline after the basic B0/B5 protocol is reviewed
Acceptance: exact source/method version, fixed resources, raw evidence and successful reproduction checks
```

### Independent reproduction

```text
Cause: the calibration audit is single-operator and all experiments ran within the project-controlled GitHub environment
Impact: no independent-reproduction credit
Next action: clean-room rerun by an independent operator after the development protocol stabilizes
```

### Runtime dependency security

```text
Cause: four high-severity findings remain in the pinned JavaScript inference dependency graph
Impact: isolated research execution only; no secure or production claim
Acceptance: zero high/critical findings or a separately approved and verified isolation boundary
```

## K. Final verdict and publication status

```text
Research verdict: INCONCLUSIVE
```

The evaluator blocker is resolved, and formal development correctness is now available. The observed direction favors EXT-B5, but the current evidence does not establish improvement, parity, superiority, equivalence or non-inferiority.

- Keep PR #2 Draft.
- Do not merge.
- Do not create a tag or GitHub Release.
- Do not begin sealed-final.
- Do not claim security, production readiness or state of the art.
