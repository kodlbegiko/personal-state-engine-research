# Personal State Engine Research

A research prototype for testing whether structured, temporal, provenance-aware personal state management improves long-horizon AI-assistant reliability under fixed model, context, tool, token and cost constraints.

> **Current status:** the fixed 20-case LongMemEval-S EXT-B0/EXT-B5 development matrix was rescored with a calibrated blinded evaluator. EXT-B5 showed a positive direction, but the sample is too small and underpowered to establish improvement.

```text
Research verdict: INCONCLUSIVE
Evidence-weighted completion: 30%
Highest evidence level: E3 — calibrated real-model external development evidence
Algorithm parity demonstrated: NO
PR state: OPEN / DRAFT
```

## Current external evidence

- Dataset: LongMemEval-S cleaned
- Frozen development cases: 20, including 4 abstention cases
- Answer trials: 40 immutable records, 0 errors, 0 timeouts
- Baselines: EXT-B0 and EXT-B5
- Answer model: `onnx-community/Qwen2.5-0.5B-Instruct`
- Answer-model revision: `956050e4c6ce7c647091e15311218f80d662559f`
- Answer-model rerun for evaluator v2: no
- Case IDs changed: no
- Sealed-final accessed: no
- Development evidence: `results/external/longmemeval-development-matrix-30676516785/`
- Evaluator v2 evidence: `results/external/longmemeval-evaluator-v2/`
- Evaluator evidence commit: `0fb95bd7d6a01f1553cfab7a28a4ca2c84bd7948`

## Evaluator v2

The project first inspected the official LongMemEval evaluator at commit `9e0b455f4ef0e2ab8f2e582289761153549043fc`. No confirmed usable OpenAI credential was available before inference, so the fixed selection policy activated a local 3B fallback while retaining official prompt semantics.

```text
Evaluator ID: longmemeval-official-prompt-priority-v2
Provider: local-fallback
Judge: onnx-community/Llama-3.2-3B-Instruct-ONNX
Judge revision: cab364e7d0e1de7aa09e3abc932be92361c5b55f
Runtime: @huggingface/transformers 4.2.0
Quantization: q4
Prompt SHA-256: be177cbb0e82bf279ad8c24e8d553ef80222464dd51c39ef7bea7231623d28e6
Parser SHA-256: 975e659fd3a109a40c8316fc532bf010a0dbf71208bcbb97978146e9d917f0e2
```

Blinded calibration used 10 cases / 20 answers:

| Metric | Observed | Required | Result |
|---|---:|---:|---|
| Raw agreement | 95.0% | >= 80% | PASS |
| Cohen's kappa | 0.7727 | >= 0.60 | PASS |
| Full-matrix invalid-output rate | 0.0% | <= 5% | PASS |

```text
Confusion matrix: TP=2 TN=17 FP=0 FN=1
Calibration verdict: PASS
Formal correctness use: PERMITTED
Audit status: single-operator blinded calibration; not independent reproduction
```

The separate 14-case evaluator-development corpus scored 13/14 with zero invalid outputs. Its one miss involved a correct core answer with a materially wrong added fact, which remains a known evaluator limitation.

## Formal development result

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

The result does not establish superiority, parity, equivalence or non-inferiority. The low absolute accuracy also indicates that the 0.5B answer model may still impose a substantial floor effect.

## Resource comparison

| Metric | EXT-B0 | EXT-B5 | B5 minus B0 |
|---|---:|---:|---:|
| Answer input tokens | 1,866 | 30,680 | +28,814 |
| Answer output tokens | 605 | 977 | +372 |
| Answer total tokens | 2,471 | 31,657 | +29,186 |
| Median answer latency | 2,009 ms | 14,222 ms | +12,213 ms |
| Recorded output storage | 22,785 bytes | 157,328 bytes | +134,543 bytes |
| Recorded monetary charge | USD 0 | USD 0 | USD 0 |

B5 produced two additional correct answers in this development sample. The recorded monetary cost per additional correct answer is USD 0 because local inference recorded no API charge; the token, latency and storage overhead remains material.

## Evidence integrity and validation

- Original raw answer trials: 40/40
- Original archive artifacts: 59/59 verified
- Evaluator v2 artifacts: 74/74 verified
- Raw judge outputs: preserved
- Baseline identity: blinded during judging
- Old failed v1 evaluator evidence: preserved
- Raw-to-summary reconstruction: PASS
- Dataset payload committed: no
- Model weights committed: no
- Sealed-final accessed: no
- Evaluator workflow: `30688327468`, success
- Complete engineering tests in evaluator workflow: 118 passed

The evaluator and completed freeze/archive workflows are manual-only after successful evidence generation. Temporary transport bundles and the bootstrap workflow were removed.

## Current gate status

| Gate | Current | Status |
|---|---:|---|
| A — Repository, sources and licensing | 10% | Complete for current inputs |
| B — Experiment infrastructure | 10% | Complete for current development contract |
| C — Basic external baselines | 10% | Calibrated B0/B5 comparison; still underpowered |
| D — Strong baseline reproduction | 0% | Not started |
| E — PSE candidate | 0% | Not started |
| F — Sealed parity test | 0% | Not started; sealed-final untouched |
| G — Independent reproduction | 0% | Not started |

```text
Evidence-weighted completion: 30%
Remaining distance: 70%
Active evidence cap: 45%
```

## Highest-value next action

Preregister a larger development comparison with a stronger fixed answer model and adequate floor-effect screening. After that protocol is stable, reproduce one pinned strong memory baseline. Do not begin sealed-final or claim algorithm parity.

## Security and publication status

The pinned JavaScript inference dependency graph still contains four unresolved high-severity findings. It remains restricted to isolated ephemeral research runners and is not a secure production runtime.

PR #2 remains Draft. Do not merge, tag or release. Do not claim parity, superiority, validation, production readiness, security or state of the art.

See [`docs/progress.md`](docs/progress.md), the [development matrix evidence](results/external/longmemeval-development-matrix-30676516785/), and the [evaluator v2 evidence](results/external/longmemeval-evaluator-v2/).

## License

MIT. Cite exact code, dataset, answer-model and evaluator revisions together with the commit SHA.
