# Candidate-v6 Development Ledger

Date: 2026-08-13
Candidate: Candidate-v6 — Assertion-Structure Evidence Objects

## Pre-implementation sequence

Preregistration was committed before Candidate-v6 implementation.

- repository reconnaissance commit: `31142656e1e47cf0690d0141e7a5c0cf30af66b5`
- failure taxonomy commit: `71177389eed8392245e37655f4e1f94a8da314ff`
- architecture comparison commit: `65ed451fbd99b4d342948d8ae78f5a1ed6d5d626`
- preregistration commit: `105a95b43d33c4b004be0b427cf85d186a58ca98`
- machine-readable preregistration config commit: `50e0e358a9f6ca76770d3eff032ba08c4bfa5a01`
- first implementation commit: `a5fcb252c37d0e7db8604a56ebd8aedbfb921ea0`

## Development benchmark materialization

Workflow: `Candidate-v6 Materialize Development Benchmark`

- run ID: `31688446771`
- triggering commit: `fb29bbfe9c7654c55e3671bbb2b016d4790e4af3`
- conclusion: SUCCESS
- generated benchmark commit: `174f5241cbe7af81efe70288db60f8e1580b535b`
- dataset SHA-256: `393f669de845a4e3443273217d880d584035135643eaa933f6096b088b4cc25d`
- cases: 120
- answerable: 50
- no-evidence/adversarial: 70

Classification: deterministic benchmark materialization, no algorithm tuning.

## Development evidence run 1

Workflow: `Candidate-v6 Development Evidence`

- run ID: `31688488856`
- job ID: `94410087985`
- head SHA: `f8e768472b75c757b013f64859a78932e4a4c1ec`
- conclusion: SUCCESS
- artifact ID: `9176385585`
- artifact digest SHA-256: `9b6155960ad6decbdc52930cd1703311f054db003c3914757bea54c694d8658d`

Tests:

- discovered/executed: 33
- passed: 33
- failed: 0

Development guardrails:

- Candidate-v6 MRR deficit vs Candidate-v2: 0.00 — PASS
- R@1 deficit: 0.00 — PASS
- R@3 deficit: 0.00 — PASS
- R@5 deficit: 0.00 — PASS
- answerable recall: 1.00 — PASS
- false abstention: 0.00 — PASS
- no-evidence false retrieval: 0.00 — PASS
- abstention accuracy: 1.00 — PASS
- absolute false-retrieval reduction vs Candidate-v2: 1.00 — PASS
- assertion extraction accuracy: 1.00 — PASS
- meta-discourse rejection accuracy: 1.00 — PASS
- explicit no-value detection accuracy: 1.00 — PASS
- contradiction detection accuracy: 1.00 — PASS
- temporal resolution accuracy: 1.00 — PASS

No Candidate-v6 development failure occurred in this first formal development-evidence run, so there is no algorithm repair to classify for run 1.

## Integrity status

- Candidate-v5 modified: NO
- Candidate-v5 protected data used as fresh validation: NO
- failed/negative evidence deleted: NO
- sealed-final newly accessed: NO
- paid API/GPU/inference: NO
- monetary cost: USD 0

Development success authorizes freeze only after repository-wide CI and benchmark-lock consistency are restored. It does not authorize Candidate-v6 selection or Gate E completion.
