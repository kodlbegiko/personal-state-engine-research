# Candidate-v6 Preregistration

Status: FROZEN PRE-IMPLEMENTATION PROTOCOL
Date: 2026-08-13
Candidate ID: `candidate-v6`
Method: `Assertion-Structure Evidence Objects`

This protocol is committed before Candidate-v6 implementation. Selection thresholds may not be loosened after observing Candidate-v6 development or protected-validation results.

## 1. Method identity

Candidate-v6 is a new research identity. It is not Candidate-v5.1 and does not modify Candidate-v5.

## 2. Method architecture

Two-stage deterministic parser:

1. **Discourse-role gate** classifies each memory before value extraction.
2. **Assertion-slot extractor** runs only on assertion-eligible text and emits typed evidence objects.

Candidate-v2 remains the frozen retrieval backend. Candidate-v6 is an independent answerability verifier and does not rerank Candidate-v2 output.

## 3. Allowed input

Candidate-v6 may read only the case query, case memories, memory IDs, memory text, timestamps, and Candidate-v2 ranking. It may not read benchmark labels, relevant-memory IDs, case IDs for decision logic, or protected-validation outcome data.

## 4. Deterministic processing path

For each case:

1. compute Candidate-v2 ranking for `k`;
2. derive required relation concepts and subject anchors from the query;
3. classify each ranked memory's discourse role;
4. if assertion-eligible, extract a typed EvidenceObject;
5. filter objects for subject/predicate/temporal compatibility;
6. detect explicit no-value, negative, unresolved, stale-only, ambiguity, or contradiction states;
7. return the original Candidate-v2 ranking unchanged only if all required query relations are supported;
8. otherwise return `[]`.

No stochastic component is allowed.

## 5. Evidence object schema

Each parsed object contains at least:

- `source_memory_id`
- `subject`
- `predicate`
- `object_or_value`
- `assertion_type`
- `polarity`
- `temporal_scope`
- `discourse_role`
- deterministic parse status

Allowed assertion/discourse types include:

- `ASSERTED_VALUE`
- `ASSERTED_RELATION`
- `NEGATED_VALUE`
- `NO_VALUE_RECORDED`
- `META_DISCUSSION`
- `QUESTION`
- `AGENDA_ITEM`
- `REVIEW_TOPIC`
- `UNRESOLVED`
- `CONTRADICTION`
- `UNKNOWN`

## 6. Assertion classification logic

Discourse/no-value/negative/unresolved patterns are evaluated before positive assertion extraction. A memory cannot support a query merely because it contains a requested relation and extra lexical residue. Support requires an explicit value-bearing grammatical/propositional slot.

## 7. Contradiction policy

Contradiction is evaluated only between comparable positive assertions with the same required subject/predicate and compatible temporal scope. Meta-discourse, questions, no-value statements, unresolved statements, and negative assertions do not create competing positive values.

Two incompatible current positive values for the same required slot without an explicit deterministic resolution cause `CONTRADICTED` and abstention.

## 8. Temporal policy

Queries containing current/latest/now/currently require non-stale support. Historical/stale assertions do not support a current query. Explicit update/correction/replacement assertions may resolve an older assertion when their temporal/status evidence is deterministic. Timestamp alone does not automatically rescue an unresolved semantic contradiction unless the assertion carries an update/current scope permitted by the parser.

## 9. Abstention policy

Fail closed on:

- missing required assertion;
- parse failure for the only potentially supporting memory;
- meta-only evidence;
- explicit no-value;
- unresolved or inferential evidence;
- stale-only current evidence;
- unsupported composition;
- incompatible contradiction or ambiguity.

## 10. Candidate-v2 relationship

Candidate-v2 ranking is frozen and remains authoritative for retrieval order. Candidate-v6 may only choose between:

- `SUPPORTED` -> return Candidate-v2 ranking unchanged;
- any unsupported verdict -> return `[]`.

No Candidate-v6 reranking is allowed.

## 11. Development benchmark policy

Create `candidate-v6-development-v1` before freeze with at least 120 deterministic cases:

- >= 50 answerable;
- >= 70 no-evidence/adversarial;
- coverage across all registered failure families;
- varied wording, relations, value types, temporal phrases, distractor order, memory order, and subject forms;
- fixed seed and canonical JSONL SHA-256.

Candidate-v5 protected failures may only inspire newly authored development regressions and must be marked `HISTORICAL_FAILURE_REGRESSION_ONLY`.

## 12. Protected-validation policy

Candidate-v6 protected validation may only be created after Candidate-v6 freeze. It must be separate from development data and from Candidate-v5 protected validation. It must contain at least 60 cases, preferably 80 if zero-cost CI capacity permits. It must be frozen before execution and formally executed once.

## 13. Frozen development success thresholds

All checks must pass before Candidate-v6 may freeze.

### Retrieval preservation vs Candidate-v2

- MRR deficit <= 0.03
- R@1 deficit <= 0.03
- R@3 deficit <= 0.02
- R@5 deficit <= 0.02

### Answerability

- answerable recall >= 0.95
- false abstention <= 0.05

### No-evidence safety

- abstention accuracy >= 0.90
- no-evidence false retrieval <= 0.10
- absolute no-evidence false retrieval reduction vs Candidate-v2 >= 0.70

### Parser diagnostics

Where deterministic ground truth exists in the development set:

- assertion extraction accuracy >= 0.95
- meta-discourse rejection accuracy >= 0.95
- explicit-no-value detection accuracy >= 0.95
- contradiction detection accuracy >= 0.95
- temporal resolution accuracy >= 0.95

## 14. Freeze conditions

Candidate-v6 may freeze only if:

1. this preregistration and machine-readable config were committed before implementation;
2. Candidate-v6 unit/regression/property tests pass;
3. development benchmark reproduces exactly;
4. every development guardrail passes;
5. repository worktree is clean in CI;
6. required CI is green;
7. benchmark lock is valid after any formal regeneration required by new eligible files;
8. no unresolved research-integrity violation exists;
9. monetary cost is USD 0;
10. no paid inference/API/GPU is used;
11. no new sealed-final access occurs;
12. Candidate-v5 remains unchanged.

## 15. Failure conditions

A development failure before freeze may be repaired only within the registered architecture. If repair requires changing method identity, selection threshold, or using future/protected outcome information, Candidate-v6 must be invalidated and a new candidate identity created.

After freeze, any selection-critical protected-validation failure rejects Candidate-v6.

## 16. Allowed debugging boundary

Before freeze, allowed:

- fix implementation bugs;
- broaden general bounded grammar based on development evidence;
- fix deterministic benchmark-generation defects;
- fix CI/infrastructure errors;
- add general regression/property tests.

Every failed run and repair classification must be preserved in the development ledger.

Not allowed even before freeze:

- case-ID branching;
- answer-string hard coding;
- benchmark-label access in the candidate;
- protected-validation result access/tuning.

## 17. Post-freeze prohibition

After Candidate-v6 freeze, no modification is allowed to:

- `src/personal_state_engine/candidate_v6.py`;
- `experiments/configs/candidate-v6-v1.json`;
- selection-critical thresholds;
- parser grammar or relation aliases;
- verifier logic.

A protected-validation failure is terminal for Candidate-v6.

## 18. Benchmark contamination policy

- Development data is diagnostic, not confirmatory.
- Candidate-v5 protected validation remains historical diagnostic evidence and is not reused as Candidate-v6 fresh validation.
- Candidate-v6 protected validation is created after freeze and cannot be edited after results.
- No rerun-until-pass behavior.

## 19. Statistics protocol

On immutable protected-validation predictions:

- paired bootstrap on answerable-case reciprocal rank;
- Candidate-v6 minus Candidate-v2 MRR delta;
- 10,000 bootstrap repetitions;
- seed `20260813`;
- 95% confidence interval;
- non-inferiority margin `0.03`;
- non-inferiority supported only if lower 95% CI bound >= `-0.03`.

Also calculate Wilson 95% intervals for:

- answerable recall;
- false abstention;
- abstention accuracy;
- no-evidence false retrieval.

## 20. Gate E decision policy

Candidate-v6 may continue to formal Gate E confirmatory selection only if all of the following hold:

1. fresh protected validation passes every frozen guardrail;
2. paired-bootstrap non-inferiority vs Candidate-v2 is supported;
3. no integrity violation invalidates the evidence.

If protected validation fails:

- Candidate-v6 = FROZEN / REJECTED;
- Gate E remains NOT COMPLETE;
- formal completion remains 45%;
- algorithm parity remains NO;
- Gate F remains NOT STARTED;
- no further adversarial work may be used to rescue Candidate-v6.

If protected validation passes, follow the existing frozen Gate E contract for any required fresh adversarial / strong-baseline / exact A-MEM comparison. Do not lower the selection standard.

## Cost and integrity constraints

- monetary cost: USD 0;
- paid API: prohibited;
- paid GPU: prohibited;
- paid inference: prohibited;
- no merge/release/tag;
- PR #2 must remain OPEN / DRAFT / NOT MERGED;
- no new sealed-final content or path-metadata access.

The objective is a credible conclusion, not a passing candidate.
