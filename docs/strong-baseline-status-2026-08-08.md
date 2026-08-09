# Gate D Strong-Baseline Mission Status — 2026-08-09 recovery reconciliation

## Current verdict

```text
Gate D: NOT COMPLETE
D1: COMPLETE
D2: COMPLETE
D3: COMPLETE
D4: NOT COMPLETE
Formal evidence-weighted completion: 30%
Algorithm parity demonstrated: NO
New monetary cost: USD 0
Sealed-final accessed: false
```

The historical `BLOCKED BY COMPUTE` state is superseded for D2/D3. Exact-pinned A-MEM executes at zero monetary cost, but the first frozen-development retrieval attempt did not complete: run `31284023872` was cancelled at the 180-minute shard timeout boundary.

## Strong baseline identity

Primary strong baseline: **A-MEM**.

- Upstream commit: `0c8039f28fdcc08189a23c07a3437d9d2482f9c2`
- Ollama model: `qwen2.5:3b`
- Dataset, case IDs, model digest and embedding snapshot remain pinned.
- No paid API or paid GPU is used.

## Reproduction layers

| Layer | Status | Evidence |
|---|---|---|
| D1 — source/protocol preparation | COMPLETE | exact source, license, runtime/model path pinned |
| D2 — exact A-MEM execution | COMPLETE | zero-cost exact-pinned runtime |
| D3 — frozen retrieval benchmark | COMPLETE | durable 24-case evidence, run `31269598248` |
| D4 — end-to-end frozen development reproduction | NOT COMPLETE | case-level recovery run `31292999631` active |

The rubric grants no partial numerical credit inside Gate D.

## Cancelled frozen-development run

Run `31284023872`:

- prepare-dataset: SUCCESS
- Python 3.11: PASS
- frozen split reproduction: PASS
- dataset identity: PASS
- exact A-MEM source pin: PASS
- Ollama digest: PASS
- embedding snapshot: PASS
- all 10 original shard jobs reached exact A-MEM execution
- all 10 were cancelled at the 180-minute job timeout boundary
- aggregate-and-persist: SKIPPED

All 10 uploaded shard artifacts were downloaded and inspected. None contained a completed `shard-N.json`; therefore valid salvaged retrieval cases = **0/20**. Large artifacts contained runtime logs only, and all `time-shard-N.txt` files were zero bytes.

Durable forensic evidence:

`results/strong-baseline/amem-development-recovery-v1/`

## Active case-level recovery

Workflow:

`.github/workflows/strong-baseline-amem-development-recovery.yml`

Run:

`31292999631`

The recovery changes execution orchestration only:

- same frozen 20 development cases / 4 abstention cases
- same `scripts/run_amem_frozen_development.py`
- same A-MEM commit/model/dataset/embedding identities
- same retrieval and scoring semantics
- `shard-count = 20`, so one frozen case per job
- timeout = 350 minutes per case job
- max parallel = 10

Recovery `prepare-dataset` and frozen split reproduction passed before case execution.

Only after 20/20 retrieval outputs pass completeness, uniqueness, provenance and hash checks may the preregistered end-to-end D4 protocol `experiments/protocols/amem-d4-development-v2.json` run.

## Existing comparative evidence

Frozen D3 MRR:

- A-MEM exact: `0.8787878788`
- PSE current: `0.9015151515`
- PSE candidate-v1: `1.0000000000`
- PSE candidate-v2: `0.9469696970`

Exact adversarial-v4 (24 total / 22 answerable):

- A-MEM MRR: `0.8333333333`
- candidate-v2 MRR: `0.875`
- paired delta: `+0.0416666667`
- 95% bootstrap CI: `[-0.10984848, +0.19696970]`
- W/T/L: `5/12/5`

Both comparisons are insufficient for formal parity/superiority. Both A-MEM and candidate-v2 fail both v4 no-evidence abstention cases.

## Integrity boundary

- Frozen development subset unchanged.
- Candidate-v2 unchanged after protected evidence.
- Failed and negative evidence preserved.
- New monetary cost: USD 0.
- Sealed-final content not accessed.
- PR #2 remains Draft / Open / Not merged.
- No tag or release.
- No parity, superiority, equivalence, non-inferiority, SOTA or production-readiness claim.
