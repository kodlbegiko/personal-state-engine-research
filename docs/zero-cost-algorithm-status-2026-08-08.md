# Zero-cost algorithm research status — 2026-08-09 reconciliation

## Verdict

`ZERO-COST ALGORITHM RESEARCH ACTIVE — D1/D2/D3 COMPLETE, D4 PENDING`

The zero-cost track has progressed beyond the historical `A-MEM NOT_EXECUTED / BLOCKED BY COMPUTE` state. Exact-pinned A-MEM now runs successfully under the repository's zero-monetary-cost boundary, and durable D3 plus adversarial-v4 evidence is committed. Formal repository completion remains 30% because Gate D is all-or-nothing under the current rubric and D4 is not yet complete.

## Current Gate D state

```text
D1 = COMPLETE
D2 = COMPLETE
D3 = COMPLETE
D4 = NOT_COMPLETE
Gate D = NOT_COMPLETE
Formal completion = 30%
Algorithm parity = NO
New monetary cost = USD 0
Sealed-final accessed = false
```

## Frozen 24-case retrieval evidence

Durable exact A-MEM run: `31269598248`.

| System | MRR |
|---|---:|
| A-MEM exact | 0.878788 |
| PSE current reconstruction | 0.901515 |
| PSE candidate-v1 | 1.000000 |
| PSE candidate-v2 | 0.946970 |

The comparison remains underpowered. Numerical ordering on this small frozen benchmark is descriptive only.

## Adversarial-v4 exact A-MEM evidence

The discriminative post-candidate-freeze adversarial-v4 benchmark contains 24 cases, of which 22 are answerable and 2 are no-evidence cases. Exact A-MEM full-corpus run `31284978045` completed successfully and persisted durable evidence.

| System | MRR | R@1 | R@5 | Abstention accuracy | False retrieval rate |
|---|---:|---:|---:|---:|---:|
| A-MEM exact | 0.833333 | 0.727273 | 1.000 | 0.000 | 1.000 |
| PSE candidate-v2 | 0.875000 | 0.772727 | 1.000 | 0.000 | 1.000 |
| Random | 0.218182 | 0.090909 | 0.500 | 0.000 | 1.000 |
| Recency | 0.465909 | 0.363636 | 0.636364 | 0.000 | 1.000 |

Candidate-v2 minus A-MEM paired MRR delta: `+0.041667`.

95% paired bootstrap CI: `[-0.109848, +0.196970]`.

Win/tie/loss: `5/12/5`.

Interpretation: **UNDERPOWERED**. Candidate-v2 is descriptively competitive with exact A-MEM on v4, but formal parity, superiority, equivalence and non-inferiority are unsupported.

## Candidate evidence

Candidate-v2 is frozen and was not retuned on adversarial-v4. Its strongest supported interpretation is a robustness-specialist candidate rather than a universal replacement for candidate-v1.

The completed 13-perturbation robustness suite shows candidate-v2 degrades substantially less than current/v1 under the tested distractor stresses. Its worst observed perturbation is `duplicate_distractor_cluster`, with approximately `-0.0909` MRR and R@1 deltas from the v4 base.

Candidate-v1 retains the lead on the normal frozen benchmark, so candidate selection must not cherry-pick a single test family.

## Abstention negative evidence

The development-only abstention strategy matrix tested:

- always retrieve
- absolute score threshold
- top1-top2 margin
- evidence coverage
- combined confidence

Under the hard guardrail that answerable development queries cannot be falsely rejected, the tested safe configurations do not separate no-evidence cases:

```text
abstention accuracy = 0
false retrieval rate = 1
false abstention rate on answerable development = 0
```

This is a retained negative result. It is currently one of the main algorithmic gaps and must not be hidden or threshold-tuned against previously observed withheld cases.

## Current active D4 precursor

A-MEM Frozen Development Retrieval:

- workflow run: `31284023872`
- Python 3.11 preflight: PASS
- frozen split reproduction: PASS
- dataset identity: PASS
- exact A-MEM commit: PASS
- Ollama model/digest: PASS
- embedding snapshot: PASS
- 10 exact A-MEM shards: executing
- scope: 20 frozen development cases / 4 abstention cases

This retrieval run is not D4 completion. After durable retrieval validation, execute the preregistered end-to-end protocol `experiments/protocols/amem-d4-development-v2.json` without changing the frozen scope or model identities.

## Integrity boundary

- Original frozen development and retrieval corpora are not changed based on results.
- Candidate-v2 freeze chronology remains before protected follow-up evidence.
- Failed evaluator and negative abstention evidence remain preserved.
- No paid API or paid GPU is used.
- Sealed-final content is not accessed.
- PR #2 remains Draft / Open / Not merged.

## Formal accounting

The evidence-gate rubric remains authoritative. D1-D3 do not receive invented partial percentage credit. Until D4 satisfies the Gate D contract, formal evidence-weighted completion remains 30%. If and only if D4 completes and validates under the repository contract, Gate D may become eligible for its 10 points and formal completion may move to 40%. Gate E must be assessed separately.
