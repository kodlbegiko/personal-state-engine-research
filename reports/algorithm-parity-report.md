# Algorithm Parity Report

Status date: 2026-07-31

## Executive verdict

```text
INCONCLUSIVE
```

Personal State Engine algorithm parity has not been demonstrated. The repository currently contains E1–E2 engineering and evaluation infrastructure, but no E3 real-model external development experiment, no E4 sealed external comparison and no E5 independent reproduction.

## Repository state reviewed

- branch: `research/personal-state-engine-v0`
- Draft PR: #2
- PR remains open and must remain Draft
- local component benchmark and curated safety regression evidence are available
- external real-model evidence is absent

## Methods reviewed

The first frontier snapshot and reproduction matrix cover basic history, summary and retrieval families and source verification for TiMem, A-MEM, AgeMem, AgentRunbook, AdaMEM and MGRetrieval. Reported paper results have not been imported as repository results.

## Reproduction status

| Category | Current result |
|---|---|
| deterministic internal component baselines | implemented and tested; not external efficacy evidence |
| external basic baselines | execution not started |
| TiMem | source verified; exact execution and license audit incomplete |
| A-MEM | source verified; exact execution and license audit incomplete |
| AgeMem | blocked by unverified implementation assets and unavailable training compute |
| PSE external candidate | hypotheses drafted; minimum model-backed candidate not executed |

No method is marked `OFFICIAL REPRODUCED`.

## Work completed in this execution pass

1. Hardened model-run manifests and subprocess response integrity.
2. Added regression tests for placeholder configuration, invalid accounting and response-ID mix-ups.
3. Expanded benchmark-lock code and tests to detect baseline, runner, path-set and anchor tampering.
4. Added current-state and resource-envelope audits.
5. Added a dated frontier snapshot and algorithm reproduction matrix.
6. Selected LongMemEval-S as the first external adapter target and LoCoMo as the planned second benchmark.
7. Implemented strict LongMemEval schema, history-rendering and hypothesis adapters.
8. Added a dataset validator that reports SHA-256 and structural counts.
9. Added machine-readable baseline selection and a non-activated preregistration.
10. Added failure taxonomy, data governance, threat model and falsifiable PSE-TMRM hypotheses.

## Validation evidence

The branch-wide CI run associated with commit `24fe46f726552eeb45a2d42a2c1178533c2b5de0` passed on Python 3.11, 3.12 and 3.13 with 82 tests before the final documentation-only commits. A new final-head CI result is required before treating the entire current branch as validated.

The latest validated run also regenerated the deterministic component benchmark, regenerated the 23-case memory-write regression set, ran descriptive analysis and confirmed that committed result artifacts did not change.

## External Benchmark status

The LongMemEval adapter is based on the official released field structure and hypothesis format. The actual dataset has not been downloaded into this environment, its license and file hash are not yet recorded, and the official evaluator has not been executed. Therefore no LongMemEval result exists.

LoCoMo has not yet received an adapter in this repository.

## PSE candidate status

The minimum proposed candidate is intentionally limited to:

- validated write policy;
- temporal validity and supersession;
- BM25 with optional pinned dense retrieval;
- explicit provenance;
- deterministic reranking;
- fixed token budget.

Graph memory, adaptive utility and learned policy remain hypotheses. They must not be added before a simpler candidate exposes a measured external bottleneck.

## Security and privacy status

Automated evidence exists for selected user isolation, injection and secret rejection, completion verification, recovery and deletion behaviours. It does not establish real-world security coverage. There is no external adversarial benchmark, no dense-vector deletion test and no full derived-memory deletion implementation.

## Gate assessment under mission v2

| Gate | Weight | Status | Earned assessment |
|---|---:|---|---:|
| A — repository, sources and licensing | 10% | EVIDENCE INCOMPLETE | 6% |
| B — experiment infrastructure | 10% | IN PROGRESS | 7% |
| C — basic external baselines | 15% | NOT STARTED | 0% |
| D — strong baseline reproduction | 20% | NOT STARTED / BLOCKED | 0% |
| E — PSE candidate | 15% | NOT STARTED | 0% |
| F — external parity test | 20% | NOT STARTED | 0% |
| G — independent reproduction | 10% | NOT STARTED | 0% |

```text
Evidence-weighted completion: 13%
```

This replaces the repository's earlier 55% pilot estimate for this mission. The v2 calculation gives most weight to external real-model evidence, which does not yet exist.

## Exact reasons parity is unproven

1. no downloaded and hash-verified external benchmark;
2. no pinned open-weight or API model available in the execution environment;
3. no real-model B0–B6 development run;
4. no faithfully reproduced strong baseline;
5. no activated preregistration or sealed final split;
6. no two-benchmark by two-model comparison;
7. no lifecycle token, latency, storage and monetary-cost comparison;
8. no cluster-aware non-inferiority analysis;
9. no calibrated evaluator or human audit;
10. no independent clean-environment reproduction;
11. committed pilot benchmark lock still has incomplete execution-boundary coverage.

## Highest-value next action

Acquire and hash the official LongMemEval-S cleaned dataset through a working network path, validate it with `scripts/validate_longmemeval.py`, then execute EXT-B0 and EXT-B5 using one pinned open-weight answer model on a development subset. This is the shortest path from E2 infrastructure to E3 real-model evidence.

## Publication decision

- keep PR #2 as Draft;
- do not merge;
- do not create a tag or release;
- do not claim parity, superiority or state of the art.
