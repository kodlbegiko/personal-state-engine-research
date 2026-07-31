# PSE-TMRM Hypotheses

Status date: 2026-07-31

`PSE-TMRM` is a working hypothesis, not a fixed architecture or novelty claim. A simpler candidate must replace it if validation shows that added modules do not justify their cost or risk.

| Module hypothesis | Expected benefit | Expected cost or failure | Measurement | Keep rule |
|---|---|---|---|---|
| temporal validity and supersession | reduce stale-state and knowledge-update errors | metadata extraction errors and missed valid history | current-state accuracy, stale-memory use, update accuracy | retain only if improvement repeats across validation settings without deletion regressions |
| sparse plus dense candidate union | improve lexical and semantic evidence recall | extra indexing, latency and duplicate candidates | evidence recall, retrieval precision, latency and token count | retain if recall improves materially and reranking controls noise |
| query-complexity routing | allocate retrieval depth and memory levels by task | router errors and extra model calls | task accuracy by type, router error and lifecycle cost | retain only if fixed-policy baselines are consistently worse |
| provenance-aware reranking | prefer inspectable and reliable evidence | may suppress useful low-confidence evidence | source faithfulness, unsupported inference and answer accuracy | retain if guardrails improve without material accuracy loss |
| contradiction and stale penalties | avoid obsolete or conflicting evidence | excessive penalty can hide legitimate historical context | conflict resolution, temporal reasoning and retrieval recall | retain only with separate current-state and historical-query evaluation |
| multi-resolution consolidation | reduce context and storage while preserving long-range facts | summary distortion and irreversible information loss | accuracy-cost frontier, source traceability and distortion rate | retain only if it creates a measurable Pareto benefit |
| temporal or causal graph | support multi-event and causal queries | graph-construction errors, complexity and latency | multi-hop accuracy, causal accuracy, edge precision and cost | optional until simpler retrieval shows a stable bottleneck |
| adaptive memory utility | suppress repeatedly harmful memories | delayed or confounded utility credit | harmful retrievals, correction rate and task-success contribution | retain only if utility predicts future benefit beyond frequency |
| learned memory controller | improve store, retrieve, update and forget decisions | training cost, reward hacking and overfitting | held-out policy performance, guardrails and lifecycle cost | prohibited until deterministic controller reaches E3 and a stable bottleneck is demonstrated |

## Minimum candidate before expansion

The first candidate must contain only:

```text
validated write policy
temporal validity and supersession
BM25 plus optional pinned dense retrieval
explicit provenance
simple deterministic reranking
fixed token budget
```

Graph construction, adaptive utility and learned control must remain disabled until the minimum candidate and basic external baselines have real-model development evidence.

## Falsification criteria

PSE-TMRM should be simplified or rejected when:

- two validation settings show no repeatable improvement;
- lifecycle cost rises by more than 20% for less than one percentage point of primary-metric improvement;
- gains occur only on a single known case, model or question type;
- a module causes material privacy, deletion, stale-memory or cross-user regression;
- the strongest result can be explained by extra context or model calls rather than memory quality.
