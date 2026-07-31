# Research Progress

Assessment date: 2026-07-31 17:09 +08:00

## Executive status

```text
Research verdict: INCONCLUSIVE
Evidence-weighted completion under mission v2: 13%
Highest evidence level reached: E2 — engineering verification
Algorithm parity demonstrated: NO
```

The earlier **55%** figure described completion of the internal engineering pilot. It is retired for the algorithm-parity mission because it gave insufficient weight to external benchmarks, real-model runs, faithful strong-baseline reproduction, sealed testing and independent replication.

## Mission v2 gate status

| Gate | Weight | Status | Earned | Verified evidence | Missing evidence |
|---|---:|---|---:|---|---|
| A — Repository, sources and licensing | 10% | EVIDENCE INCOMPLETE | 6% | Repository and Draft PR are inspectable; dated source snapshot, reproduction matrix, resource audit and baseline-selection manifest exist | Complete dataset and code licensing audit; downloaded dataset hashes; immutable source revisions for every executed method |
| B — Experiment infrastructure | 10% | IN PROGRESS | 7% | Strict model manifests, replay/subprocess adapters, trial schema, scoring utilities, tamper tests, LongMemEval adapter and validator | Integrated external trial runner; pinned model runtime; lifecycle cost capture; activated preregistration |
| C — Basic external baselines | 15% | NOT STARTED | 0% | EXT-B0–EXT-B6 are specified | No real-model runs on a hash-verified external benchmark |
| D — Strong baseline reproduction | 20% | NOT STARTED / BLOCKED | 0% | TiMem, A-MEM, AgeMem, AgentRunbook, AdaMEM and MGRetrieval are tracked in the reproduction matrix | No method has been faithfully reproduced and validated under matched conditions |
| E — PSE candidate | 15% | NOT STARTED | 0% | Falsifiable PSE-TMRM hypotheses and a minimum candidate boundary are documented | No external development run; no measured ablation; no evidence supporting graph, adaptive or learned modules |
| F — External parity test | 20% | NOT STARTED | 0% | Non-inferiority decision framework exists as a draft | No two-benchmark × two-model sealed comparison; no calibrated evaluator; no cluster-aware analysis |
| G — Independent reproduction | 10% | NOT STARTED | 0% | Clean GitHub-hosted CI runs are reproducible | No separate operator, clean-room run or independent implementation reproduction |

```text
Total evidence-weighted completion: 13%
```

## Completed in the latest execution pass

### Experiment integrity

- Hardened `RunManifest` against blank identifiers, placeholder versions, unexpected fields, invalid types and non-finite values.
- Rejected negative token and latency accounting.
- Enforced subprocess response `request_id` matching.
- Added replay and subprocess failure-path regression coverage.

### Benchmark integrity

- Added support for SHA-256 and Git blob SHA-1 verification.
- Added regression tests for baseline, runner, lock-anchor, path-set and path-traversal tampering.
- Preserved Issue #3 as open because the committed `pilot-v0.3` manifest still does not cover the complete execution boundary.

### External benchmark preparation

- Implemented an official-shape LongMemEval adapter.
- Added strict validation for question, session, timestamp, evidence-turn and answer-session structure.
- Added history rendering and hypothesis JSONL support.
- Added `scripts/validate_longmemeval.py` to report SHA-256 and structural counts.
- Added eight LongMemEval fixture and CLI tests.
- Selected LongMemEval-S as the first external benchmark and LoCoMo as the planned second benchmark.

### Research governance

- Added current-state and resource-envelope audits.
- Added a dated frontier snapshot and algorithm reproduction matrix.
- Added machine-readable external baseline selection.
- Added a non-activated preregistration draft.
- Added data-governance, security-threat-model, algorithm-failure-taxonomy and PSE-TMRM hypothesis documents.
- Added `reports/algorithm-parity-report.md` with the `INCONCLUSIVE` verdict.

## Latest verified validation

Final implementation head before this documentation refresh:

```text
8178b9cb0f90893a9aa882fc84d9b8b7b0203ca4
```

GitHub Actions run **#56** completed successfully on:

- Python 3.11
- Python 3.12
- Python 3.13

Each job completed:

- editable package installation;
- source and test compilation;
- **90 automated tests**;
- pilot benchmark-lock verification;
- deterministic component benchmark regeneration;
- 23-case memory-write regression regeneration;
- descriptive analysis;
- clean `results/` diff verification.

## Evidence that is valid now

- The engineering implementation and regression suite are reproducible on three Python versions.
- The internal B0–B7 benchmark is useful for deterministic component regression.
- The 23-case memory-write corpus currently yields 15/15 attack-or-secret rejections and 8/8 benign acceptances.
- The LongMemEval adapter can parse and validate official-shape fixtures and produce hypothesis files.
- Selected persistence, user-isolation, deletion, recovery and trusted-verification behaviours have automated tests.

These results are **E2 engineering evidence only**. They do not establish real-world effectiveness, security coverage, parity or state-of-the-art performance.

## Evidence that does not yet exist

- downloaded, license-reviewed and hash-verified LongMemEval-S data;
- pinned open-weight or API model execution;
- real-model EXT-B0–EXT-B6 results;
- faithful strong-baseline reproduction;
- activated preregistration and sealed final split;
- two-benchmark × two-model comparison;
- lifecycle token, latency, storage and monetary-cost comparison;
- evaluator calibration and human audit;
- cluster-aware non-inferiority analysis;
- independent clean-environment reproduction.

## Highest-value next action

Acquire and hash the official LongMemEval-S cleaned dataset through an authorized network path, validate it with `scripts/validate_longmemeval.py`, then execute EXT-B0 and EXT-B5 with one pinned answer model on a development subset while preserving raw outputs, manifests, token usage, latency and failure records.

Until this produces E3 evidence, adding graph memory, reinforcement learning or a learned controller is not justified.

## Publication status

- PR #2 remains **Draft**.
- Do not merge to `main`.
- Do not create a tag or GitHub Release.
- Do not claim parity, superiority or state of the art.
