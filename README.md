# Personal State Engine Research

A research prototype for testing whether structured, temporal, provenance-aware personal state management improves long-horizon AI-assistant reliability compared with no memory, full-history replay, rolling summaries and similarity-only retrieval.

> **Current status:** engineering and evaluation pilot. The repository contains a tested reference architecture, deterministic component benchmark, persistent deletion tests, recovery controls, trial schemas, scoring utilities and a small memory-write red team. It does **not** yet establish improved real-LLM task performance.

## Research question

Can a Personal State Engine combining selective memory, temporal versioning, commitment tracking, controlled proactive intervention and evidence-backed completion outperform simpler memory baselines under fixed model, tool and token constraints?

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
- Tamper-detecting benchmark lock
- Provider-neutral replay and subprocess model adapters
- Validated trial-record schema and independent structured scorer
- Wilson interval and exact paired-comparison utilities
- 23-case multilingual memory-write red team with benign controls
- 70 automated tests

## What the evidence means

The B0–B7 component benchmark checks whether each architecture exposes specific capabilities under controlled deterministic scenarios. It is useful for regression and architectural validation. Because capabilities are intentionally added across B4–B7, the scores are architecture-sensitive and are **not** proof that B7 is superior in real model use.

The memory-write red team currently passes all 23 frozen cases: 15 malicious-or-secret cases are rejected and 8 benign controls are accepted. This is performance on a small curated corpus, not a real-world attack coverage estimate.

No hypothesis is marked `SUPPORTED`. A valid efficacy result still requires at least two pinned models, repeated controlled runs, an untouched final set, independent adjudication, cost/latency evidence and independent reproduction.

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

Generated evidence:

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

## Repository map

```text
src/personal_state_engine/   implementation, persistence, adapters, records and scoring
benchmarks/synthetic/        component scenarios
benchmarks/redteam/          memory-write safety corpus
benchmarks/pilot/            hash lock
experiments/                 provider-neutral run configuration
scripts/                     reproducible runners
results/raw/                 machine-readable observations
results/processed/           summaries and descriptive analysis
reports/                     pilot research reports
tests/                       unit, integration, persistence, recovery and security tests
docs/                        protocol, architecture, limitations and gate status
```

## Current gate status

The conservative weighted completion estimate is **55%**. Gate 0 is passed; later gates remain incomplete or in progress. See [`docs/progress.md`](docs/progress.md).

## Security and privacy

Do not place real credentials, private conversations, medical records, precise addresses, identity documents or other high-risk personal data in the benchmark. See [`SECURITY.md`](SECURITY.md) and [`docs/privacy-threat-model.md`](docs/privacy-threat-model.md).

## License

MIT. Cite exact code and data versions using [`CITATION.cff`](CITATION.cff) and the commit SHA.
