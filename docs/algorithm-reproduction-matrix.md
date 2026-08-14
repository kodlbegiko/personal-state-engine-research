# Algorithm Reproduction Matrix

Status date: 2026-08-10

No row in this table is a formal parity or superiority claim. `COMPLETE` means the repository-defined evidence layer named in the row is durably supported; it does not imply independent reproduction or sealed-final validation.

| Method | Family | Source / implementation | Zero-cost execution state | Current evidence | Remaining gap |
|---|---|---|---|---|---|
| B0 no cross-session memory | basic | internal | COMPLETE | frozen LongMemEval development EXT-B0 answers preserved | low development accuracy; broad B0–B7 model-backed issue remains open |
| Recent-history replay | basic | internal | COMPLETE / auxiliary | deterministic development evidence exists | not a selected strong baseline |
| Rolling summary | basic | internal | auxiliary | development infrastructure exists | not a selected strong baseline |
| BM25 sparse retrieval | retrieval | internal | COMPLETE / auxiliary | frozen comparison evidence exists | not an independent reproduction target |
| TF-IDF retrieval | retrieval | internal | COMPLETE / auxiliary | frozen comparison evidence exists | not an independent reproduction target |
| PSE current | temporal structured retrieval | internal | COMPLETE / development | frozen normal/adversarial evidence exists | no formal parity claim |
| PSE candidate-v1 | temporal structured retrieval | internal frozen candidate | COMPLETE / development | leads candidate-v2 on the normal frozen retrieval benchmark | weaker tested adversarial robustness than v2 |
| PSE candidate-v2 | temporal structured retrieval | internal frozen candidate | COMPLETE / development | stronger tested robustness; adversarial-v4 MRR 0.875 | no formal universal selection; abstention unresolved; independent reproduction false |
| A-MEM | structured linked memory | `WujiangXu/A-mem` commit `0c8039f28fdcc08189a23c07a3437d9d2482f9c2` | D1/D2/D3/D4 COMPLETE | exact adversarial-v4 evidence plus accepted 20/20 frozen development recovery and D4 end-to-end evidence at USD 0 | strongest candidate comparison remains underpowered; no independent parity claim |
| TiMem | temporal-hierarchical | external source previously reviewed | not current primary target | source-level evidence only | exact compatible reproduction not completed |
| AgeMem | learned policy | external | blocked by present zero-cost resource boundary | source-level evidence only | training assets/GPU/resources |
| AgentRunbook-R/C | experience/query-time construction | external | not currently feasible at full scale | source-level evidence only | implementation/data/sandbox requirements |

## Primary strong-baseline target — COMPLETE FOR GATE D

```text
Primary method: exact-pinned A-MEM
Source commit: 0c8039f28fdcc08189a23c07a3437d9d2482f9c2
Zero-cost model path: qwen2.5:3b
D1: COMPLETE
D2: COMPLETE
D3: COMPLETE
D4: COMPLETE
Gate D: COMPLETE
```

The original two-case-per-job frozen-development run `31284023872` was cancelled by its 180-minute execution timeout. Its artifacts contained no completed shard JSON and provided 0/20 formally salvageable cases. That failure remains preserved.

Case-level recovery run `31292999631` retained the same frozen cases, A-MEM source commit, `qwen2.5:3b` model digest, embedding snapshot, dataset identity and scoring semantics. It completed with exactly 20 valid unique cases, zero missing, zero duplicate and zero invalid cases. Durable retrieval evidence is `results/strong-baseline/amem-development-v1/predictions-run1.json`.

The preregistered D4 run `31316152994` then completed successfully under `experiments/protocols/amem-d4-development-v2.json`, with 20/20 answer trials, judge invalid rate 0, recorded monetary cost USD 0 and no sealed-final access.

## Comparative claim boundary

Exact A-MEM adversarial-v4 run `31284978045` is complete. On 22 answerable cases:

```text
A-MEM MRR:            0.833333
PSE candidate-v2 MRR: 0.875000
v2 minus A-MEM:      +0.041667
paired bootstrap 95% CI: [-0.109848, +0.196970]
W/T/L: 5 / 12 / 5
```

The frozen A-MEM-v4 protocol explicitly marks answerable `n < 30` as underpowered. The interval crosses zero. This supports descriptive competitiveness only and does not establish parity, superiority, equivalence or non-inferiority.

Abstention is also unresolved: both exact A-MEM and candidate-v2 false-retrieved on the v4 no-evidence cases. A deeper development diagnostic is preserved in `results/continuation-mission/maximum-capability-progress-2026-08-10.json`; the currently exposed candidate-v2 top-score, margin and coverage confidence features are not safely separable under the zero-false-abstention guardrail.

## Current Gate E / Gate G state

Gate E remains `NOT_COMPLETE / NO_FORMAL_SELECTION`:

- candidate-v1 retains the normal-benchmark lead;
- candidate-v2 remains the frozen robustness specialist rather than a justified universal replacement;
- candidate-v2 versus exact A-MEM remains statistically underpowered;
- abstention remains unresolved;
- independent reproduction is false.

Candidate selection synthesis is preserved in `results/continuation-mission/gate-e-candidate-selection-matrix-v1.json`.

Gate G remains `NOT_COMPLETE`:

- E3 `artifact-registry-v2` provenance hardening is implemented;
- a fresh `External E3 Smoke` run is still required;
- post-upload GitHub artifact ID/digest archival is still required;
- the current execution environment can inspect/rerun existing Actions but cannot create a new `workflow_dispatch` run;
- official-faithful evaluator v3 remains blocked by the exact-runtime requirement under the zero-cost boundary.

No state above authorizes sealed-final, merge, release, parity, superiority, equivalence or non-inferiority claims.
