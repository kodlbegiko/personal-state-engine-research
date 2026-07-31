# Research Progress

Assessment date: 2026-07-31 18:04 +08:00

## Executive status

```text
Research verdict: INCONCLUSIVE
Evidence-weighted completion under mission v2: 15%
Highest evidence level reached: E2 — engineering verification
Algorithm parity demonstrated: NO
```

The increase from 13% to 15% reflects two bounded changes only: the official LongMemEval-S source contract is now pinned and checksum-enforced, and an integrated immutable `EXT-B0` / `EXT-B5` trial vertical slice is current-head CI verified. No credit was added to Gates C–G because no real model external result exists.

## Mission v2 gate status

| Gate | Weight | Status | Earned | Verified evidence | Missing evidence |
|---|---:|---|---:|---|---|
| A — Repository, sources and licensing | 10% | EVIDENCE INCOMPLETE | 7% | Repository and Draft PR are inspectable; official LongMemEval-S cleaned source, revision, MIT license, size and SHA-256 are pinned; checked downloader and failure tests exist | Actual payload download and audit; split hashes; complete licensing review for every executed method and model |
| B — Experiment infrastructure | 10% | IN PROGRESS | 8% | Strict model manifest and adapters; integrated `EXT-B0` / `EXT-B5` runner; immutable raw trial record; request/model/config attribution; error retention; v0.4 lock and current-head CI | Complete model-manifest snapshot reference; actual runtime manifest; lifecycle cost implementation; matrix runner; artifact registry; activated preregistration |
| C — Basic external baselines | 15% | NOT STARTED | 0% | `EXT-B0` and deterministic BM25 `EXT-B5` are executable through one contract | No real-model run on downloaded, hash-verified external data |
| D — Strong baseline reproduction | 20% | NOT STARTED / BLOCKED | 0% | TiMem and other candidates are tracked | No faithful clean-environment reproduction under matched conditions |
| E — PSE candidate | 15% | NOT STARTED | 0% | Minimum candidate boundary and falsifiable hypotheses are documented | No external PSE-Min implementation result or ablation |
| F — External parity test | 20% | NOT STARTED | 0% | Non-inferiority framework remains a draft | No activated preregistration, sealed final matrix, evaluator calibration or cluster-aware analysis |
| G — Independent reproduction | 10% | NOT STARTED | 0% | GitHub-hosted CI reproduces E2 engineering checks | No independent operator or clean-room result reconstruction |

```text
Total evidence-weighted completion: 15%
E2 completion cap: 20%
Cap binding: NO — evidence-weighted Gate total is lower than the cap
```

## Completed in this execution pass

### Integrated external trial path

- Added one formal external-trial entrypoint for LongMemEval cases.
- Implemented `EXT-B0` without cross-session history.
- Implemented deterministic BM25 `EXT-B5` session retrieval with fixed tie-breaking.
- Persisted dataset, split, model, request, prompt and configuration attribution.
- Preserved token, latency, raw output, error and timeout fields.
- Made raw trial files exclusive-create and non-overwritable.
- Added five runner tests covering B0 isolation, BM25 selection, attribution, failure retention and collision rejection.

### Dataset source and integrity

- Pinned `xiaowu0162/longmemeval-cleaned` revision `98d7416c24c778c2fee6e6f3006e7a073259d48f`.
- Pinned `longmemeval_s_cleaned.json` at 277,383,467 bytes with SHA-256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`.
- Recorded MIT license and a conservative derived-results-only repository policy.
- Added a streaming downloader that refuses floating revisions and overwrites, verifies size and hash, and removes invalid partial files.
- Added four dataset-source and download-failure tests.
- Excluded downloaded benchmark payloads and external raw trials from accidental source commits.

### Benchmark integrity

- Committed `pilot-v0.4` using Git blob SHA-1 for all current package modules, Python runners and internal benchmark corpora.
- Added lock anchor `22e7b10880005af05b8b4276c13f1d2904816f9b2ba4289938ee9e208082ee23`.
- CI now regenerates the lock and anchor, requires no diff, checks the expected path set, verifies the anchor, and then regenerates committed internal outputs.
- Issue #3 remains open because configuration, dependency and external-anchor boundaries still need a final completeness review.

## Latest implementation validation

Implementation head:

```text
51fe1dc67539d1ea45c44caeb228a4b31290d152
```

GitHub Actions run **#86** succeeded on Python 3.11, 3.12 and 3.13. Each job completed:

- editable installation;
- compilation;
- **99 automated tests**;
- v0.4 lock regeneration and clean-diff check;
- expected-path and anchor verification;
- deterministic component benchmark regeneration;
- 23-case memory-write regression regeneration;
- descriptive analysis;
- committed-results clean-diff verification.

## Evidence interpretation

Valid now:

- E2 engineering evidence that the external trial path, provenance checks, failure retention, dataset source contract and v0.4 integrity checks behave as tested.
- E2 deterministic evidence that the existing internal benchmark outputs remain reproducible.

Not valid now:

- external-model effectiveness;
- LongMemEval score;
- BM25 improvement over no memory;
- PSE algorithm parity;
- faithful strong-baseline reproduction;
- production readiness or general security claims.

## Blocking evidence

- LongMemEval-S is source-pinned but not downloaded or locally audited.
- No exact real model/runtime is available in the execution environment.
- No `EXT-B0` or `EXT-B5` real-model raw trial exists.
- No evaluator calibration, lifecycle cost comparison, strong baseline, sealed matrix or independent reproduction exists.

## Highest-value next action

In a network-enabled and credentialed environment, run the checked LongMemEval downloader, validate and split the dataset, pin one exact model/runtime and execute 3–5 real `EXT-B0` and `EXT-B5` smoke cases. Preserve every success, error and timeout as immutable raw records. Do not expand PSE-Min before this first E3 evidence exists.

## Publication status

- PR #2 remains **Draft**.
- Do not merge to `main`.
- Do not create a research tag or GitHub Release.
- Do not claim parity, superiority, validation or state of the art.
