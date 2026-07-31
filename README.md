# Personal State Engine Research

A research prototype for testing whether structured, temporal, provenance-aware personal state management improves long-horizon AI-assistant reliability compared with no memory, full-history replay, rolling summaries and retrieval baselines.

> **Current status:** engineering and external-evaluation preparation. The repository contains a tested reference architecture, deterministic component benchmark, model-run integrity controls, persistence and deletion tests, recovery controls, a LongMemEval adapter, trial schemas, scoring utilities and a small memory-write red team. It does **not** yet establish improved real-LLM task performance or algorithm parity.

```text
Research verdict: INCONCLUSIVE
Evidence-weighted completion under mission v2: 13%
Highest evidence level reached: E2 — engineering verification
```

## Research question

Can a Personal State Engine combining selective memory, temporal versioning, commitment tracking, controlled proactive intervention and evidence-backed completion outperform or match strong memory baselines under fixed model, tool, token and cost constraints?

## Implemented

- Working, episodic, semantic and procedural memory types
- Provenance, confidence, validity intervals and supersession
- Conservative durable-memory write policy with Unicode normalization
- In-memory and SQLite user-scoped stores
- Temporal filtering, hybrid retrieval and token-budget selection
- SQLite schema/integrity checks, concurrent writers and compacted deletion of implemented indexes
- Commitment ledger, proactive threshold and duplicate suppression
- Optional trusted completion evidence, digest validation and false-completion rejection
- Verified rollback before alternative recovery actions
- Deterministic B0–B7 component baselines
- Nine split-labelled pilot scenarios and 72 observations
- Benchmark tamper detection and execution-boundary regression tests
- Strict replay and subprocess model adapters
- Validated model-run manifests and immutable trial records
- Independent structured scorer, Wilson intervals and exact paired-comparison utilities
- Official-shape LongMemEval parsing, validation, history rendering and hypothesis JSONL support
- 23-case multilingual memory-write red team with benign controls
- **90 automated tests**

## What the evidence means

The internal B0–B7 component benchmark checks whether each architecture exposes specific capabilities under controlled deterministic scenarios. It is useful for regression and architectural validation. Because capabilities are intentionally added across B4–B7, the scores are architecture-sensitive and are **not** proof that B7 is superior in real model use.

The memory-write red team currently passes all 23 frozen cases: 15 malicious-or-secret cases are rejected and 8 benign controls are accepted. This is performance on a small curated corpus, not a real-world attack coverage estimate.

The LongMemEval adapter has been tested against official-shape fixtures, but the actual benchmark has not yet been downloaded, license-reviewed, hash-verified or executed with a real model. No LongMemEval result currently exists.

No efficacy hypothesis is marked `SUPPORTED`. A valid parity result still requires pinned models, real external benchmark runs, faithful strong-baseline reproduction, an activated preregistration, sealed testing, cost and latency evidence, evaluator calibration and independent reproduction.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m compileall -q src scripts experiments/runners tests
python -m unittest discover -s tests -v
python scripts/verify_benchmark_lock.py
python scripts/run_benchmark.py
python scripts/run_redteam.py
python scripts/analyze_component_results.py
```

Validate an authorized LongMemEval dataset copy:

```bash
python scripts/validate_longmemeval.py /path/to/longmemeval_s.json
```

Generated internal evidence:

```text
results/raw/component_benchmark.jsonl
results/processed/component_benchmark_summary.json
results/processed/component_benchmark_statistics.json
results/raw/memory_write_redteam.jsonl
results/processed/memory_write_redteam_summary.json
```

## Current component benchmark

| Baseline | Description | Passed | Total | Pass rate |
|---|---|---:|---:|---:|
| B0 | No cross-session memory | 4 | 9 | 44.44% |
| B1 | Full replay with finite context | 2 | 9 | 22.22% |
| B2 | Rolling summary | 4 | 9 | 44.44% |
| B3 | Similarity-only retrieval | 3 | 9 | 33.33% |
| B4 | Structured user-scoped state | 6 | 9 | 66.67% |
| B5 | B4 plus temporal validity | 7 | 9 | 77.78% |
| B6 | B5 plus commitments and proactive control | 8 | 9 | 88.89% |
| B7 | B6 plus completion verification | 9 | 9 | 100.00% |

The statistics output contains an explicit warning that its intervals and exact paired tests describe only this fixed case set.

## Latest validation

GitHub Actions run **#56** passed on Python 3.11, 3.12 and 3.13 at implementation head `8178b9cb0f90893a9aa882fc84d9b8b7b0203ca4`.

Each job ran compilation, all 90 tests, pilot-lock verification, internal benchmark and red-team regeneration, descriptive analysis and a clean committed-results diff check.

## Repository map

```text
src/personal_state_engine/   implementation, persistence, adapters, records and scoring
benchmarks/synthetic/        internal component scenarios
benchmarks/redteam/          memory-write safety corpus
benchmarks/pilot/            pilot benchmark lock
experiments/                 run configuration, selection and preregistration drafts
scripts/                     reproducible runners and dataset validators
results/raw/                 machine-readable internal observations
results/processed/           summaries and descriptive analysis
reports/                     pilot and algorithm-parity reports
tests/                       unit, integration, persistence, adapter, recovery and security tests
docs/                        protocol, architecture, audits, governance and progress status
```

## Current gate status

The mission-v2 evidence-weighted completion estimate is **13%**. Engineering verification has reached E2, while real-model external baselines, strong-method reproduction, sealed parity testing and independent reproduction have not started.

See:

- [`docs/progress.md`](docs/progress.md)
- [`reports/algorithm-parity-report.md`](reports/algorithm-parity-report.md)
- [`docs/algorithm-reproduction-matrix.md`](docs/algorithm-reproduction-matrix.md)
- [`experiments/preregistration.md`](experiments/preregistration.md)

## Highest-value next action

Acquire and hash an authorized copy of LongMemEval-S, validate it, then execute EXT-B0 and EXT-B5 with one pinned model on a development subset while preserving raw outputs, manifests, token usage, latency and failures.

## Security and privacy

Do not place real credentials, private conversations, medical records, precise addresses, identity documents or other high-risk personal data in the benchmark. See [`SECURITY.md`](SECURITY.md), [`docs/data-governance.md`](docs/data-governance.md) and [`docs/security-threat-model.md`](docs/security-threat-model.md).

## Publication status

PR #2 remains Draft. Do not merge, tag, release or claim parity until the model-backed and independent-reproduction acceptance criteria are met.

## License

MIT. Cite exact code and data versions using [`CITATION.cff`](CITATION.cff) and the commit SHA.
