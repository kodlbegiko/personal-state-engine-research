# Personal State Engine Research

A research prototype for testing whether structured, temporal, provenance-aware personal state management improves long-horizon AI-assistant reliability under fixed model, context, tool, token and cost constraints.

> **Current status:** the fixed LongMemEval-S EXT-B0/EXT-B5 development matrix completed at the raw-evidence level, but the semantic evaluator failed calibration. Formal answer-quality comparison is blocked.

```text
Research verdict: BLOCKED
Evidence-weighted completion: 24%
Highest evidence level: E3 — real-model external development evidence
Algorithm parity demonstrated: NO
PR state: OPEN / DRAFT
```

## Current external evidence

- Dataset: LongMemEval-S cleaned
- Dataset revision: `98d7416c24c778c2fee6e6f3006e7a073259d48f`
- Dataset SHA-256: `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`
- Frozen development cases: 20
- Baselines: EXT-B0 and EXT-B5
- Answer model: `onnx-community/Qwen2.5-0.5B-Instruct`
- Model/tokenizer revision: `956050e4c6ce7c647091e15311218f80d662559f`
- Runtime: `@huggingface/transformers 4.2.0`, q4, GitHub-hosted Ubuntu CPU runner
- Formal trials: 40 completed, 0 model errors, 0 timeouts
- Sealed-final accessed: no
- Durable evidence commit: `333f1019470facd35775d7f2ed314b9191db12dd`
- Evidence directory: `results/external/longmemeval-development-matrix-30676516785/`

The raw evidence contract passed: unique trial/request IDs, EXT-B0 history exclusion, EXT-B5 retrieval trace, raw-to-summary reconstruction, artifact hashes, failure retention and sealed-final non-access.

## Evaluator blocker

The semantic judge cannot be used for formal correctness:

```text
Full-matrix invalid output rate: 27.5%   (required <= 5%)
Blinded-audit raw agreement: 15.4%       (required >= 80%)
Cohen's kappa: 0.0                       (required >= 0.60)
Valid-output confusion: TP=2 TN=0 FP=11 FN=0
Calibration verdict: FAIL
Formal correctness use: PROHIBITED
```

Therefore this repository does **not** report formal B0/B5 accuracy, paired wins/losses, McNemar results, effect size, parity, superiority, equivalence or non-inferiority. Issue #6 tracks the required evaluator replacement and calibration.

## Supported findings

- The pinned dataset, model, runtime and unchanged frozen 20-case subset can execute end to end.
- EXT-B0 and EXT-B5 each produced 20 immutable raw answer trials.
- BM25 retrieved at least one answer-bearing session in 18/20 cases as a post-hoc retrieval diagnostic.
- EXT-B5 used a fixed 1,024 lexical-token history budget; all 20 B5 cases required truncation.
- EXT-B5 added 28,814 answer-input tokens and about 12.2 seconds median answer latency relative to EXT-B0 in this configuration.

These are engineering, retrieval and resource observations only. Correctness-denominated cost ratios are undefined until an evaluator passes calibration.

## Validation

GitHub Actions run `30676516773` passed on Python 3.11, 3.12 and 3.13 with 109 tests, benchmark-lock verification, existing E3 contract verification, deterministic benchmark regeneration and red-team regeneration.

The evidence archive workflow re-downloaded Actions artifact `8810812462`, re-ran the development evidence contract, verified 59 archived artifacts and 40 raw trials, excluded dataset payload/model weights, and committed the durable archive.

## Repository map

```text
src/personal_state_engine/   implementation, persistence, adapters and evidence records
benchmarks/                  deterministic component and red-team corpora
experiments/                 protocols, model/config manifests and frozen splits
scripts/                     dataset, experiment and evidence verification runners
results/external/            durable external model evidence
reports/                     research reports
Tests/                       not used; tests live in tests/
tests/                       unit, integration, persistence and security regressions
docs/                        governance, architecture and progress status
```

## Current gate status

| Gate | Previous | Current | Status |
|---|---:|---:|---|
| A — Repository, sources and licensing | 9% | 10% | Complete for current sources |
| B — Experiment infrastructure | 9% | 10% | Complete for current development contract |
| C — Basic external baselines | 2% | 4% | Raw matrix complete; evaluator blocked |
| D — Strong baseline | 0% | 0% | Not started |
| E — PSE candidate | 0% | 0% | Prohibited until baseline stability |
| F — Sealed parity test | 0% | 0% | Not started; sealed-final untouched |
| G — Independent reproduction | 0% | 0% | Not started |

```text
Evidence-weighted completion: 24%
Remaining distance: 76%
Active evidence cap: 45%
```

## Highest-value next action

Replace the failed semantic evaluator with the official pinned LongMemEval evaluator or a stronger blinded judge, then rescore the unchanged 40 raw outputs and pass the preregistered calibration thresholds. Do not expand to EXT-B1–EXT-B6, PSE-Min or sealed-final before that gate passes.

## Security and publication status

The captured JavaScript dependency graph still contains four unresolved high-severity findings. It is restricted to isolated ephemeral research runners and is not a secure production runtime.

PR #2 remains Draft. Do not merge, tag or release. Do not claim parity, superiority, validation, production readiness, security or state of the art.

See [`docs/progress.md`](docs/progress.md), [Issue #6](../../issues/6), and the [durable development evidence](results/external/longmemeval-development-matrix-30676516785/).

## License

MIT. Cite exact code, dataset, model and evaluator revisions together with the commit SHA.
