# Current State Audit

Audit timestamp: 2026-08-09T11:55:00+08:00

## Repository state

```yaml
working_branch: research/personal-state-engine-v0
pull_request: 2
pr_state: open
pr_draft: true
pr_merged: false
research_verdict: INCONCLUSIVE
evidence_weighted_completion: 30_percent
algorithm_parity_demonstrated: false
new_monetary_cost_usd: 0
sealed_final_content_accessed: false
```

This audit is evidence-first. Workflow names, README claims and historical status text are not treated as proof without durable artifacts and GitHub Actions state.

## Formal gate state

```text
Gate A: COMPLETE
Gate B: COMPLETE
Gate C: COMPLETE
Gate D: NOT COMPLETE
  D1: COMPLETE
  D2: COMPLETE
  D3: COMPLETE
  D4: NOT COMPLETE — case-level recovery active
Gate E: NOT COMPLETE
Gate F: NOT STARTED — sealed-final prohibited
Gate G: NOT COMPLETE — independent reproduction false
```

Gate D receives no invented partial percentage. Formal completion therefore remains 30% until D4 satisfies its frozen acceptance contract.

## Verified strong-baseline evidence

Exact-pinned A-MEM source commit:

`0c8039f28fdcc08189a23c07a3437d9d2482f9c2`

Frozen 24-case D3 run `31269598248` completed durably. Exact adversarial-v4 run `31284978045` also completed durably.

On adversarial-v4 (24 total / 22 answerable):

- A-MEM MRR: `0.8333333333`
- PSE candidate-v2 MRR: `0.875`
- paired delta: `+0.0416666667`
- 95% bootstrap CI: `[-0.10984848, +0.19696970]`
- W/T/L: `5/12/5`

The result is underpowered and does not establish parity, superiority, equivalence or non-inferiority. A-MEM and candidate-v2 both failed both no-evidence abstention cases.

## Frozen development retrieval incident and recovery

Original run `31284023872` passed Python 3.11, frozen split, dataset, exact source, Ollama digest and embedding-snapshot checks, but all ten two-case shard jobs hit the 180-minute execution timeout. Aggregate/persist was skipped.

All ten uploaded artifacts were inspected. None contained a completed `shard-N.json`; formally salvageable retrieval cases = `0/20`. The failure is preserved under:

`results/strong-baseline/amem-development-recovery-v1/`

Active recovery run: `31292999631`.

Recovery is execution-only:

- same frozen 20 development cases / 4 abstention cases
- same A-MEM/model/dataset/embedding identities
- same existing retrieval runner and scoring semantics
- 20 case-level shards, one case per job
- 350-minute job timeout
- maximum 10 concurrent case jobs

Recovery dataset preparation and frozen split reproduction have passed. D4 cannot start until 20/20 retrieval outputs validate with no missing, duplicate or invalid cases.

## Candidate and evaluator boundary

Candidate-v2 remains frozen and is best described as a robustness specialist, not a formally selected universal replacement for candidate-v1. Candidate-v1 retains the lead on the normal frozen retrieval benchmark.

Evaluator-v2 development calibration remains:

```text
raw agreement: 95.0%
Cohen kappa: 0.7727
invalid-output rate: 0.0%
formal development correctness use: permitted
independent reproduction: false
```

Abstention remains unresolved negative evidence: under the no-false-abstention guardrail, tested safe confidence strategies have abstention accuracy `0` and false retrieval rate `1`.

## Integrity / publication decision

- frozen development scope unchanged;
- candidate-v2 not retuned after protected evidence;
- failed and negative evidence preserved;
- no paid API or paid GPU used;
- sealed-final content not accessed;
- keep PR #2 Draft and Open;
- do not merge, tag or release;
- do not claim parity, superiority, validation, security, production readiness or state of the art.
