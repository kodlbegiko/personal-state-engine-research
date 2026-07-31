# Current State Audit

Audit timestamp: 2026-07-31T18:04:00+08:00

## Repository state

```yaml
auditor: OpenAI autonomous research agent
default_branch: main
working_branch: research/personal-state-engine-v0
implementation_head: 51fe1dc67539d1ea45c44caeb228a4b31290d152
pull_request: 2
pr_state: open
pr_draft: true
pr_mergeable: true
base_commit: 0b415e69383908188528cbdccba71fd78d53c224
current_head_ci: run 86 success
```

The repository, branch, PR, commits, changed files, issues and workflow metadata were re-read through the authenticated GitHub connector. README and prior progress claims were not treated as source-of-truth evidence.

## Confirmed engineering evidence

- An integrated LongMemEval external-trial vertical slice now supports `EXT-B0` and deterministic BM25 `EXT-B5` request construction.
- Every attempted trial receives a request ID, run ID, model provider, model ID, exact model revision, dataset and split hashes, prompt and configuration hashes, token accounting, latency, raw output or classified error, and immutable output path.
- Raw trial files use exclusive creation and cannot be overwritten in place; failed adapter calls remain retained as error or timeout records.
- The official LongMemEval-S cleaned source is pinned to Hugging Face revision `98d7416c24c778c2fee6e6f3006e7a073259d48f`, with expected size `277383467` bytes and SHA-256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`.
- The checked downloader rejects floating URLs, size drift, hash mismatch and overwrite attempts, and removes partial files on verification failure.
- `pilot-v0.4` now locks all current package modules, Python runners and the two internal benchmark corpora using Git blob SHA-1 values.
- CI regenerates the lock and anchor, requires a clean diff, validates the expected path set, verifies the anchor, and then regenerates committed deterministic results.

## Current-head validation

GitHub Actions run **#86** passed against implementation head:

```text
51fe1dc67539d1ea45c44caeb228a4b31290d152
```

Python 3.11, 3.12 and 3.13 each completed:

```text
editable install
compile
99 automated tests
benchmark-lock v0.4 regeneration and clean-diff check
expected-path and anchor verification
component benchmark regeneration
memory-write regression regeneration
descriptive analysis
committed-result clean-diff check
```

The verified lock anchor was:

```text
22e7b10880005af05b8b4276c13f1d2904816f9b2ba4289938ee9e208082ee23
```

## Evidence inventory added in this pass

```text
src/personal_state_engine/external_trials.py
scripts/run_external_trial.py
tests/test_external_trials.py
experiments/datasets/longmemeval-s-cleaned.json
scripts/fetch_longmemeval.py
tests/test_dataset_fetch.py
benchmarks/pilot/benchmark-lock.json
benchmarks/pilot/benchmark-lock.sha256
```

## Interpretation boundary

This pass raises engineering readiness only. It does not create E3 evidence because:

- the full LongMemEval-S payload was not downloaded into an executable environment;
- no pinned real model was invoked;
- no real-model raw output exists;
- no scored EXT-B0 or EXT-B5 development comparison exists;
- no strong baseline was reproduced.

The deterministic adapter, fixture and unit-test results remain E2 and must not be presented as model effectiveness.

## Confirmed blockers

1. The interactive container cannot resolve external DNS; local `git clone`, dataset download and model download fail through the ordinary network path.
2. No usable provider credential or local inference runtime was available for a real-model run.
3. No GPU was available in the audited local environment.
4. The dataset source, license, revision, size and expected digest are pinned, but the actual payload and local audit output do not yet exist.
5. Benchmark lock v0.4 protects the current package modules, runners and internal corpora, but Issue #3 remains open until benchmark configuration, dependency and external-anchor semantics are reviewed as a complete release boundary.
6. Issue #4 remains open until the immutable trial record includes or references an independently stored complete validated model-manifest snapshot, not only its normalized fields and configuration hash.

## Highest-value next action

Use a network-enabled, credentialed execution environment to download and verify the pinned LongMemEval-S file, produce the dataset audit and development split manifest, pin one exact model/runtime, and execute real `EXT-B0` and `EXT-B5` smoke trials. Until those raw trials exist, the research remains at E2 and the verdict remains `INCONCLUSIVE`.
