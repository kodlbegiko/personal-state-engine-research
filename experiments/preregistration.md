# Parity Experiment Preregistration

Status: `DRAFT_NOT_ACTIVATED`

Created: 2026-07-31

This document prevents exploratory work from being reported as confirmatory evidence. No sealed test may be opened and no parity claim may be made until all activation fields below are pinned in a committed amendment.

## Research question

Does a Personal State Engine candidate memory method achieve non-inferior answer accuracy relative to the strongest successfully reproduced memory baseline, while avoiding material safety, privacy, token, latency or storage regressions?

## Planned primary comparison

```yaml
candidate: PSE candidate algorithm, exact version not yet selected
reference: strongest successfully reproduced baseline
primary_benchmark: LongMemEval-S
secondary_benchmark: LoCoMo
primary_metric: official benchmark QA accuracy
non_inferiority_margin_percentage_points: -3
secondary_decision_rule: Pareto parity under the repository protocol
```

## Planned baseline families

- no cross-session memory;
- full or bounded recent history;
- rolling summary;
- dense retrieval;
- BM25 sparse retrieval;
- sparse-dense hybrid retrieval;
- one temporal or hierarchical strong method;
- one structurally different strong method when resources allow.

Existing deterministic component methods named B0–B7 are not the external efficacy baselines in this preregistration.

## Statistical plan

- paired comparisons on identical question IDs;
- report point estimates, counts, failed runs and confidence intervals;
- use paired bootstrap that preserves the highest available shared-history or scenario grouping;
- use McNemar's test where binary paired labels and assumptions are appropriate;
- report effect size and accuracy-cost Pareto results;
- control multiple confirmatory comparisons;
- do not replace the primary metric after viewing sealed results.

## Evaluator plan

The official deterministic evaluator is preferred when available. LongMemEval QA uses an LLM judge, so formal activation must pin:

- evaluator source revision;
- judge model and revision;
- judge prompt hash;
- retry and parse-failure policy;
- blinded method names and randomized presentation where pairwise judging is used;
- human audit sample;
- judge-human agreement reporting.

## Run-failure policy

- provider, timeout, parse and missing-output failures remain in the run ledger;
- failures are handled by a committed rule, not silently deleted;
- retries use a fixed maximum;
- a method with materially higher failure rate cannot be declared non-inferior from successful cases alone.

## Guardrails

Parity is disallowed if the candidate materially worsens any preregistered threshold for:

- stale-memory use;
- conflict or supersession error;
- deletion leakage;
- cross-user contamination;
- persistent prompt injection;
- false completion;
- sensitive-data over-retention;
- unsupported inference.

## Cost accounting

Record write, extraction, indexing, consolidation, update, retrieval, reranking, context construction, generation and maintenance costs. Do not report only answer-generation tokens.

## Activation blockers

This preregistration is not active because the following are not yet pinned:

1. dataset files and hashes;
2. sealed split and access record;
3. two exact model revisions;
4. strong reference baseline and exact source commit;
5. candidate algorithm version;
6. evaluator model and prompt hash;
7. repetitions, seeds and retry ceiling;
8. cost ceiling;
9. human audit sample and adjudication procedure;
10. missing-data and exclusion rules.

## Activation rule

Create a committed amendment containing every blocker above before any sealed test is accessed. If any primary setting changes after sealed access, the affected result is exploratory and cannot support `PARITY ACHIEVED`.
