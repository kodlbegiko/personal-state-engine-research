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

The fixed 20-case LongMemEval-S EXT-B0/EXT-B5 development matrix was rescored with evaluator v2. The evaluator passed every preregistered calibration threshold, so formal development-set correctness statistics are permitted. EXT-B5 scored higher than EXT-B0, but the sample contains only four discordant pairs and does not establish a reliable effect.

## A. GitHub and evidence state

```text
Research branch: research/personal-state-engine-v0
Development evidence commit: 333f1019470facd35775d7f2ed314b9191db12dd
Evaluator v2 evidence commit: 0fb95bd7d6a01f1553cfab7a28a4ca2c84bd7948
Formal matrix workflow: 30676516785
Evaluator v2 workflow: 30688327468
Evaluator v2 job: 91338369889
Evaluator workflow result: SUCCESS
Complete tests in evaluator workflow: 118 passed
PR #2: OPEN / DRAFT / NOT MERGED
Issue #6: evaluator blocker resolved
Tag: none
Release: none
```

The evaluator and completed freeze/archive workflows are now manual-only. Temporary transport bundles and the bootstrap workflow were removed after durable-evidence verification.

## B. Fixed protocol and source evidence

```text
Protocol: experiments/protocols/longmemeval-development-matrix-v2.json
Frozen split: experiments/splits/longmemeval-development-matrix-v1.json
Cases: 20
Abstention cases: 4
Case-ID SHA-256: 519b4db13813b60ad6a49cce919543b0639524a98bd1b0d1615c53e62cf8cc7e
Answer trials: 40
Answer-model rerun: false
Case IDs changed: false
Sealed-final accessed: false
```

```text
Dataset: LongMemEval-S cleaned
Dataset revision: 98d7416c24c778c2fee6e6f3006e7a073259d48f
Dataset SHA-256: d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442
Answer model: onnx-community/Qwen2.5-0.5B-Instruct
Answer-model revision: 956050e4c6ce7c647091e15311218f80d662559f
Runtime: @huggingface/transformers 4.2.0, q4
```

Evidence directories:

```text
results/external/longmemeval-development-matrix-30676516785/
results/external/longmemeval-evaluator-v2/
```

The original v1 evaluator failure remains unchanged. Evaluator v2 preserves blinded inputs, unblinding key, 54 raw judge outputs, parsed judgments, the original blinded audit, calibration, formal rescoring, paired analysis, manifests and a 74-file registry.

## C. Evaluator source and selection

Official evaluator source:

```text
Repository: https://github.com/xiaowu0162/LongMemEval
Commit: 9e0b455f4ef0e2ab8f2e582289761153549043fc
Path: src/evaluation/evaluate_qa.py
License: MIT
Official judge: gpt-4o-2024-08-06
```

No confirmed usable OpenAI credential was available before inference, and the GitHub CPU runner could not reasonably reproduce the official local 70B route. The fixed selection policy therefore chose the pinned local fallback before any result was observed:

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

The parser accepts only exact `yes` or `no` outputs, case-insensitive, with an optional terminal period or exclamation mark. Every other output is retained as `INVALID`.

## D. Evaluator development corpus

The 14-case unit corpus was separate from the 40 formal answers.

```text
Cases: 14
Valid outputs: 14
Invalid outputs: 0
Correct classifications: 13
Accuracy: 92.86%
```

The one miss accepted a response containing the correct core answer plus a materially wrong added fact. This remains a known limitation.

## E. Blinded calibration

```text
Audit: 10 cases / 20 answers
Audit type: single-operator blinded calibration; not independent reproduction
Scorable: 20
Unscorable: 0
Valid judge outputs: 20
Invalid judge outputs: 0
```

| Metric | Observed | Required | Result |
|---|---:|---:|---|
| Raw agreement | 95.0% | >= 80% | PASS |
| Cohen's kappa | 0.7727 | >= 0.60 | PASS |
| Full-matrix invalid rate | 0.0% | <= 5% | PASS |
| Abstention accuracy | 100% | — | — |
| Sensitivity | 66.7% | — | limited positive recall |
| Specificity | 100% | — | — |
| PPV | 100% | — | — |
| NPV | 94.4% | — | — |

```text
TP=2 TN=17 FP=0 FN=1
Calibration verdict: PASS
Formal correctness use: PERMITTED
```

All fixed gates passed. Confidence remains limited because the audit contains only three human-positive examples and no independent second operator.

## F. Formal rescoring

| Metric | EXT-B0 | EXT-B5 | Difference |
|---|---:|---:|---:|
| Correct | 2/20 | 4/20 | +2 |
| Accuracy | 10.0% | 20.0% | +10.0 percentage points |
| Wilson 95% interval | 2.8%–30.1% | 8.1%–41.6% | wide and overlapping |

```text
B5 wins: 3
B5 losses: 1
Both correct: 1
Both incorrect: 15
Discordant pairs: 4
Exact McNemar two-sided p-value: 0.625
Effect interpretation: directional but inconclusive improvement
```

The development result does not establish improvement. The large p-value is not evidence of equivalence, no effect or non-inferiority.

## G. Resource comparison

| Metric | EXT-B0 | EXT-B5 | B5 minus B0 |
|---|---:|---:|---:|
| Answer input tokens | 1,866 | 30,680 | +28,814 |
| Answer output tokens | 605 | 977 | +372 |
| Answer total tokens | 2,471 | 31,657 | +29,186 |
| Median answer latency | 2,009 ms | 14,222 ms | +12,213 ms |
| Recorded output storage | 22,785 bytes | 157,328 bytes | +134,543 bytes |
| Recorded monetary charge | USD 0 | USD 0 | USD 0 |

B5 produced two additional correct answers in this fixed sample. Recorded monetary cost per additional correct answer is USD 0 because local inference recorded no API charge. This is not evidence that B5 is economically free; token, latency and storage overhead are substantial.

## H. Evidence integrity

```text
Original raw trials: 40/40
Original archive artifacts: 59/59 verified
Evaluator v2 artifacts: 74/74 verified
Formal parsed judgments: 40
Unit parsed judgments: 14
Raw judge outputs preserved: yes
Baseline blinding: PASS
Raw-to-summary reconstruction: PASS
Old failed evaluator preserved: PASS
Dataset payload committed: no
Model weights committed: no
Sealed-final accessed: false
```

A temporary compatibility symlink tree was used only to resolve archived registry paths for the original verifier. It was removed immediately after verification and did not alter evidence bytes.

## I. Gate assessment

| Gate | Previous | Current | Status |
|---|---:|---:|---|
| A — Repository, sources and licensing | 10% | 10% | Complete for current inputs |
| B — Experiment infrastructure | 10% | 10% | Complete for current development contract |
| C — Basic external baselines | 4% | 10% | Calibrated B0/B5 comparison; underpowered |
| D — Strong baseline reproduction | 0% | 0% | Not started |
| E — PSE candidate | 0% | 0% | Not started |
| F — Sealed parity test | 0% | 0% | Not started; sealed-final untouched |
| G — Independent reproduction | 0% | 0% | Not started |

```text
Previous completion: 24%
Current completion: 30%
Remaining distance: 70%
Active evidence cap: 45%
```

## J. Remaining blockers

### Statistical and answer-model adequacy

```text
Cause: 20 paired cases, four discordant pairs, low absolute accuracy and a 0.5B answer model
Evidence: B0 2/20, B5 4/20, exact McNemar p=0.625
Impact: no supported efficacy or parity conclusion
Next action: preregister a larger development comparison with a stronger fixed answer model and floor-effect screening
```

### Strong-baseline gap

```text
Cause: no faithful published strong memory baseline has been reproduced
Impact: active evidence cap remains 45%; parity cannot be assessed
Next action: reproduce one exact-pinned strong baseline after reviewing the basic B0/B5 protocol
```

### Independent reproduction

```text
Cause: calibration was single-operator and experiments ran in the project-controlled GitHub environment
Impact: no independent-reproduction credit
Next action: clean-room rerun after the development protocol stabilizes
```

### Runtime dependency security

```text
Cause: four high-severity findings remain in the pinned JavaScript inference dependency graph
Impact: isolated research execution only; no secure or production claim
Acceptance: zero high/critical findings or a separately approved, verified isolation boundary
```

## K. Final verdict and publication status

```text
Research verdict: INCONCLUSIVE
```

The evaluator blocker is resolved. Formal development correctness is available, and its direction favors EXT-B5, but the current evidence does not establish improvement, parity, superiority, equivalence or non-inferiority.

- Keep PR #2 Draft.
- Do not merge.
- Do not create a tag or GitHub Release.
- Do not begin sealed-final.
- Do not claim security, production readiness or state of the art.
