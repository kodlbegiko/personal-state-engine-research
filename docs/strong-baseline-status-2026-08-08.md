# Gate D Strong-Baseline Mission Status — 2026-08-09 reconciliation

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

The historical `BLOCKED BY COMPUTE` status is superseded. Exact-pinned A-MEM now executes successfully in the zero-cost GitHub Actions path. Gate D remains incomplete only because the repository-defined D4 end-to-end frozen development reproduction has not yet completed.

## Strong baseline identity

Primary strong baseline: **A-MEM**.

- Upstream commit: `0c8039f28fdcc08189a23c07a3437d9d2482f9c2`
- License: MIT
- Ollama path: `qwen2.5:3b`
- Exact model digest and embedding snapshot are retained in durable run evidence.
- No paid API or paid GPU is used.

## Reproduction layers

| Layer | Status | Evidence |
|---|---|---|
| D1 — source/protocol reproduction preparation | COMPLETE | exact source, license, runtime/model path pinned |
| D2 — exact A-MEM execution | COMPLETE | successful zero-cost exact-pinned runtime |
| D3 — frozen retrieval benchmark | COMPLETE | durable 24-case A-MEM evidence, run `31269598248` |
| D4 — end-to-end frozen development reproduction | NOT COMPLETE | development retrieval precursor run `31284023872` executing |

The repository rubric does not grant partial numerical credit inside Gate D. Therefore D1-D3 completion alone does not move formal completion above 30%.

## D3 frozen 24-case result

Durable evidence: `results/strong-baseline/amem-frozen-24-v1/`.

Observed retrieval MRR on the frozen comparison:

- A-MEM exact: `0.8787878788`
- PSE current reconstruction: `0.9015151515`
- PSE candidate-v1: `1.0000000000`
- PSE candidate-v2: `0.9469696970`

This set is underpowered and does not establish parity, superiority, equivalence or non-inferiority.

## Exact A-MEM adversarial-v4

Workflow run `31284978045` completed all 8 shards plus aggregate/persist successfully. Durable evidence is committed under:

`results/strong-baseline/amem-adversarial-v4-full-v1/`

On 24 total cases / 22 answerable cases:

| System | MRR | Recall@1 | Recall@5 | Abstention accuracy |
|---|---:|---:|---:|---:|
| A-MEM exact | 0.833333 | 0.727273 | 1.000 | 0.000 |
| PSE candidate-v2 | 0.875000 | 0.772727 | 1.000 | 0.000 |

Paired candidate-v2 minus A-MEM MRR delta: `+0.041667`.

95% paired bootstrap CI: `[-0.109848, +0.196970]`.

Win / tie / loss for candidate-v2 versus A-MEM: `5 / 12 / 5`.

Interpretation: **UNDERPOWERED**. The two systems are descriptively competitive on this operator-designed adversarial set, but the interval crosses zero and the answerable sample is below the preregistered n=30 threshold. Both systems false-retrieve on both no-evidence cases.

## Current D4 precursor

Active workflow:

- `.github/workflows/strong-baseline-amem-development.yml`
- run ID: `31284023872`
- Python: 3.11
- frozen development split reproduction: PASS
- source/model/embedding identity checks: PASS
- scope: 20 frozen development cases, including 4 abstention cases
- 10 exact A-MEM shards: currently executing

Do not rerun, cancel, alter the protocol, alter the frozen manifest, or change model identities while this run remains valid and in progress.

If durable retrieval outputs complete successfully, the next repository-defined action is the already-preregistered end-to-end protocol:

`experiments/protocols/amem-d4-development-v2.json`

Only a validated D4 completion can make Gate D eligible for its 10-point rubric credit.

## Integrity boundary

- Frozen LongMemEval development subset unchanged.
- Existing immutable EXT-B0/EXT-B5 answers unchanged.
- Frozen retrieval corpora are not modified in response to results.
- Failed/negative evidence remains preserved.
- New monetary cost: USD 0.
- Sealed-final content not accessed.
- PR #2 remains Draft / Open / Not merged.
- No tag or release.

## Current next gate

Complete and validate frozen development retrieval, then execute and validate D4 end-to-end at zero monetary cost. Gate E work may continue independently, but no result in this document authorizes sealed-final or a parity claim.
