# Zero-cost algorithm research status — 2026-08-09 recovery reconciliation

## Verdict

`ZERO-COST ALGORITHM RESEARCH ACTIVE — D1/D2/D3 COMPLETE, D4 RECOVERY ACTIVE`

Formal repository completion remains **30%** because Gate D is all-or-nothing and D4 has not completed. Algorithm parity remains **NO**.

```text
D1 = COMPLETE
D2 = COMPLETE
D3 = COMPLETE
D4 = NOT_COMPLETE
Gate D = NOT_COMPLETE
Gate E = NOT_COMPLETE
Formal completion = 30%
New monetary cost = USD 0
Sealed-final accessed = false
```

## Durable exact A-MEM evidence already complete

Frozen 24-case run `31269598248`:

| System | MRR |
|---|---:|
| A-MEM exact | 0.878788 |
| PSE current | 0.901515 |
| PSE candidate-v1 | 1.000000 |
| PSE candidate-v2 | 0.946970 |

Exact adversarial-v4 run `31284978045` (24 total / 22 answerable):

| System | MRR | R@1 | R@5 | Abstention accuracy |
|---|---:|---:|---:|---:|
| A-MEM exact | 0.833333 | 0.727273 | 1.000 | 0.000 |
| PSE candidate-v2 | 0.875000 | 0.772727 | 1.000 | 0.000 |

Candidate-v2 minus A-MEM MRR delta: `+0.041667`; 95% paired bootstrap CI `[-0.109848, +0.196970]`; W/T/L `5/12/5`. The comparison remains **UNDERPOWERED** and does not establish parity or superiority.

## Cancelled frozen-development retrieval

Original run `31284023872` is **CANCELLED**, not in progress and not successful.

Verified preflight before cancellation:

- Python 3.11: PASS
- frozen split reproduction: PASS
- dataset identity: PASS
- exact A-MEM commit: PASS
- Ollama model/digest: PASS
- embedding snapshot: PASS

All 10 original shard jobs reached exact A-MEM execution and were cancelled at the 180-minute job timeout boundary. Aggregate/persist was skipped.

All 10 cancelled-run artifacts were downloaded and inspected. None contained a completed `shard-N.json`; valid salvaged retrieval cases = **0/20**. Forensic inventory and coverage are preserved under:

`results/strong-baseline/amem-development-recovery-v1/`

## Active zero-cost case-level recovery

Workflow:

`.github/workflows/strong-baseline-amem-development-recovery.yml`

Run:

`31292999631`

Recovery changes execution orchestration only:

- same frozen 20 development cases / 4 abstention cases
- same A-MEM commit and existing runner script
- same dataset/model/embedding identities
- same retrieval/scoring semantics
- one frozen case per job (`shard-count = 20`)
- 350-minute job timeout
- max parallel = 10
- no paid API / paid GPU

Recovery dataset preparation and frozen split reproduction passed. D4 may not start until 20/20 recovered retrieval cases validate with no missing, duplicate or invalid outputs.

## Candidate / abstention boundary

Candidate-v2 remains a frozen robustness specialist rather than a formally selected universal replacement for v1. Candidate-v1 retains the normal frozen benchmark lead, while v2 is stronger under the tested adversarial/perturbation stresses.

The development abstention strategy matrix remains negative evidence: under the no-false-abstention guardrail, tested safe confidence strategies have `abstention_accuracy = 0` and `false_retrieval_rate = 1`. This result is preserved and is not retuned against observed withheld cases.

## Integrity boundary

- Frozen benchmark/development scope unchanged.
- Candidate-v2 not retuned after protected evidence.
- Failed and negative evidence preserved.
- No paid API or paid GPU.
- Sealed-final content not accessed.
- PR #2 remains Draft / Open / Not merged.
- No merge, tag or release.

Only a validated 20/20 development retrieval followed by the frozen `experiments/protocols/amem-d4-development-v2.json` end-to-end run can make Gate D eligible for its 10 rubric points and formal completion eligible to move from 30% to 40%.
