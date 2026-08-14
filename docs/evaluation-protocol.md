# Evaluation Protocol

## Current component benchmark

The current benchmark contains nine synthetic scenarios and eight architecture baselines. Each scenario creates a fresh baseline instance and records observed and expected behaviour.

The runner produces 72 JSONL observations and a baseline summary. A separate analysis script computes Wilson intervals and exact paired McNemar comparisons, while explicitly marking them as descriptive of this fixed, architecture-sensitive case set only.

## Interpretation constraint

B4–B7 contain capabilities that B0–B3 intentionally lack. Pass-rate differences therefore show implementation coverage of benchmarked invariants, not causal evidence of superior LLM performance. The intervals are not population estimates, and the paired p-values must not be presented as real-model efficacy evidence.

## Pilot integrity

The nine cases carry development, validation and `pilot_test` labels. These labels validate the pipeline only: all cases have already been inspected, so none is an untouched final test set. `benchmarks/pilot/benchmark-lock.json` hashes scenario data, the component evaluator, the memory-write red-team corpus, policy, scoring code and runners. CI fails on unrecorded changes.

## Memory-write red team

The current corpus contains 23 curated cases:

- 15 multilingual, obfuscated prompt-injection or credential cases expected to be rejected;
- 8 benign controls expected to be accepted.

The current policy passes all 23 cases. This measures only the frozen corpus and is not an estimate of real-world attack coverage.

## Required model-backed protocol

Before a research verdict:

1. Build and freeze a larger untouched final set.
2. Pin at least two exact model versions.
3. Hold tools, prompts, temperature, token budgets and timeouts constant where possible.
4. Run repeated trials with fixed and varied seeds.
5. Store each run in the validated `TrialRecord` schema.
6. Use a scorer separate from the system under test and independently adjudicate a sample.
7. Report means, medians, distributions, confidence intervals, paired effects, costs and latency.
8. Preserve raw outputs, errors, timeouts and negative results.
9. Re-run primary analysis from a clean environment.

## Primary metrics

- task success;
- stale-memory use;
- cross-user contamination;
- deletion leakage;
- false completion;
- intervention precision and recall;
- unnecessary interruption;
- token use, latency and cost.
