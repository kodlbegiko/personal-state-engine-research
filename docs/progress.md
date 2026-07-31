# Research Progress

Assessment date: 2026-08-01 01:50 +08:00

## Executive status

```text
Research verdict: INCONCLUSIVE
Evidence-weighted completion under mission v2: 20%
Highest evidence level reached: E3 — real-model external smoke evidence
Algorithm parity demonstrated: NO
```

The repository now contains the first real-model LongMemEval-S evidence. This is a four-case development smoke run for pipeline and attribution validation. It is not a development matrix, confirmatory evaluation, strong-baseline comparison or parity result.

## First E3 evidence

```text
Evidence commit: 2728fc9fc11076db2be9418edea9520c8195b333
Source branch head: ca98c4789a7836651bde87f2d6b93fb140d737b0
Archive workflow run: 30652039317
Run ID: e3-smoke-30652039317-attempt-1
Evidence label: REAL-MODEL SMOKE — E3 PIPELINE EVIDENCE
```

### Dataset

```text
Dataset: LongMemEval-S cleaned
Source revision: 98d7416c24c778c2fee6e6f3006e7a073259d48f
License: MIT
File size: 277383467 bytes
SHA-256: d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442
Questions: 500
Sessions: 23867
Turns: 246750
Validation failures: 0
```

The source file was downloaded twice through pinned GitHub Actions workflows and matched the expected size and SHA-256. The 277 MB payload is not committed. The repository stores the source manifest, audit, split manifests and derived evidence.

### Model and runtime

```text
Model: HuggingFaceTB/SmolLM2-135M-Instruct
Model revision: 12fd25f77366fa6b3b4b768ec3050bf629380bac
Tokenizer revision: 12fd25f77366fa6b3b4b768ec3050bf629380bac
Quantization: q4
Runtime: @huggingface/transformers 4.2.0
Node: v24.18.0
Hardware: GitHub-hosted ubuntu-24.04 CPU runner
Model cache size: 184178727 bytes
Model q4 SHA-256: 933577110303a2964096d19b6f15d3b4639bef7f99481ac0b61d9f3ad72f392a
```

`experiments/runtime/package-lock.json` is committed. The reusable smoke workflow now uses `npm ci` and is manual-only.

### Paired smoke result

| Metric | EXT-B0 | EXT-B5 |
|---|---:|---:|
| Cases | 4 | 4 |
| Completed | 4 | 4 |
| Errors | 0 | 0 |
| Timeouts | 0 | 0 |
| Provisional correct | 0 | 0 |
| Input tokens | 361 | 14749 |
| Output tokens | 228 | 256 |
| Total tokens | 589 | 15005 |
| Median latency | 1652 ms | 20933 ms |
| Recorded output storage | 4972 bytes | 70070 bytes |
| API spend | USD 0 | USD 0 |

All four paired provisional differences were zero. This does not establish equivalence or non-inferiority. The evaluator is a deliberately limited deterministic diagnostic rather than the official semantic evaluation process, and the selected 135M model is a pipeline model rather than a competitive answer model.

## Evidence integrity

Durably committed evidence includes:

- dataset audit;
- development, validation and sealed-final split manifests;
- smoke-selection manifest;
- exact model cache file hashes;
- environment manifest;
- eight immutable raw trial records;
- processed summary;
- artifact registry with per-file SHA-256;
- dependency audit;
- exact npm lockfile;
- archive provenance record.

The artifact registry contains 16 entries. External inspection confirmed that all registry hashes match the committed files, all eight trial IDs and request IDs are unique, EXT-B0 has no retrieved history, EXT-B5 has one retrieved session per case, and summary counts tie exactly to raw records.

## Mission v2 gate status

| Gate | Weight | Status | Earned | Verified evidence | Missing evidence |
|---|---:|---|---:|---|---|
| A — Repository, sources and licensing | 10% | IN PROGRESS | 9% | Pinned and audited LongMemEval-S source, exact hash, license, deterministic splits and durable audit | Complete redistribution review for every future benchmark and strong method |
| B — Experiment infrastructure | 10% | IN PROGRESS | 9% | Pinned model/runtime, immutable raw trials, token/latency/storage capture, artifact registry, reproducible manual workflow | Official evaluator, full lifecycle compute accounting and stronger external anchoring |
| C — Basic external baselines | 15% | SMOKE ONLY | 2% | Four paired real-model EXT-B0 and EXT-B5 cases with raw outputs | At least 20–50 predetermined development cases, EXT-B1–EXT-B6, competitive model and calibrated evaluation |
| D — Strong baseline reproduction | 20% | NOT STARTED / BLOCKED | 0% | Candidate methods tracked | No faithful strong-baseline reproduction |
| E — PSE candidate | 15% | NOT STARTED | 0% | PSE-Min boundary documented | No external PSE-Min run or ablation |
| F — External parity test | 20% | NOT STARTED | 0% | Draft decision framework only | No activated preregistration or sealed matrix |
| G — Independent reproduction | 10% | NOT STARTED | 0% | GitHub-hosted engineering and smoke runs are inspectable | No independent operator or clean-room reproduction |

```text
Total evidence-weighted completion: 20%
Evidence-level cap: 45% because E3 exists without a faithful strong baseline
```

## Open risks and blockers

1. `npm audit` reports four high-severity findings in the smoke runtime dependency graph, involving `@huggingface/transformers`, `onnxruntime-node`, `adm-zip` and `sharp`. No automatic fix was available in the captured audit. The smoke ran in an isolated ephemeral GitHub runner and must not be treated as a secure production runtime.
2. The provisional evaluator scored every case as incorrect; an official or calibrated semantic evaluator is still required.
3. EXT-B5 used roughly 25 times the input tokens of EXT-B0 and materially higher latency on this smoke sample.
4. Only four selected development cases and one small model were executed.
5. No strong baseline, PSE-Min external experiment, sealed test or independent reproduction exists.

## Highest-value next action

Run a predetermined 20–50-case LongMemEval-S development subset using the same raw-evidence contract, a more capable pinned model, EXT-B0 and EXT-B5, and an official or calibrated evaluator. Do not expand PSE architecture before this basic matrix is stable.

## Publication status

- PR #2 remains Draft.
- Do not merge to `main`.
- Do not create a research tag or GitHub Release.
- Do not claim parity, superiority, validation, production readiness or state of the art.
