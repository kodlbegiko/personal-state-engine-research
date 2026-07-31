# Algorithm Failure Taxonomy

Status date: 2026-07-31

This taxonomy separates memory-system failures from base-model, evaluator and infrastructure failures. Every confirmed failure should receive a minimal reproducer and a regression test before its proposed fix is retained.

| Code | Definition | Primary evidence |
|---|---|---|
| `write_omission` | Useful information was not persisted. | source turn, write decision and later query |
| `write_overcapture` | Irrelevant or unsafe information was persisted. | stored record and policy trace |
| `wrong_memory_type` | Information was stored under an incorrect memory class. | expected and actual type |
| `bad_consolidation` | Consolidation merged incompatible facts or lost necessary distinctions. | source records and derived record |
| `summary_distortion` | A summary changed, invented or removed material facts. | source history and summary diff |
| `retrieval_miss` | Relevant evidence existed but was not retrieved. | gold evidence and candidate set |
| `retrieval_noise` | Irrelevant evidence displaced useful context. | ranked candidates and token budget |
| `stale_memory_use` | Expired or superseded information was treated as current. | validity interval and response evidence |
| `conflict_resolution_failure` | Contradictory records were not resolved or surfaced. | conflict graph and selected evidence |
| `temporal_reasoning_failure` | Dates, order, duration or current-state inference was wrong. | timeline and answer trace |
| `causal_link_failure` | Unsupported or missing causal relationships changed the answer. | graph edges and source evidence |
| `router_failure` | Query classification selected an inappropriate retrieval policy. | router output and counterfactual policy |
| `reranker_failure` | Relevant candidates were generated but ranked too low. | candidate and score components |
| `context_budget_failure` | Truncation or allocation removed required evidence. | token ledger and discarded evidence |
| `base_model_failure` | Correct evidence was supplied but the answer model still failed. | complete prompt and model output |
| `evaluation_failure` | The evaluator misparsed, misjudged or inconsistently scored output. | evaluator input, raw output and adjudication |
| `memory_poisoning` | Untrusted content persisted and influenced later behaviour. | provenance, write path and later response |
| `privacy_failure` | Sensitive or cross-user information was stored or retrieved improperly. | user scope, data classification and trace |
| `provenance_failure` | Source identity or evidence lineage was missing or forged. | record metadata and source locator |
| `delete_propagation_failure` | Deleted content remained in an index, summary, cache or derived record. | deletion trace and residual artifact |
| `cost_regression` | A change increased lifecycle cost beyond its measured benefit. | before-and-after token and monetary ledger |
| `latency_regression` | A change increased end-to-end latency beyond its measured benefit. | before-and-after latency distribution |

## Required correction loop

```text
failure case
→ minimal reproduction
→ taxonomy assignment
→ at least two candidate fixes
→ development comparison
→ validation confirmation
→ regression test
→ cost and guardrail check
→ retain or revert
```

A successful anecdote is insufficient to merge an algorithmic change. A failure may receive multiple codes when evidence shows multiple independent causes, but the primary cause must be identified for statistical reporting.
