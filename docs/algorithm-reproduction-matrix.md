# Algorithm Reproduction Matrix

Status date: 2026-08-09

No row in this table is a formal parity or superiority claim. `COMPLETE` means the repository-defined evidence layer named in the row is durably supported; it does not imply independent reproduction or sealed-final validation.

| Method | Family | Source / implementation | Zero-cost execution state | Current evidence | Remaining gap |
|---|---|---|---|---|---|
| B0 no cross-session memory | basic | internal | COMPLETE | frozen development EXT-B0 answers preserved | low development accuracy; no sealed-final |
| Recent-history replay | basic | internal | COMPLETE / auxiliary | deterministic development evidence exists | not a selected strong baseline |
| Rolling summary | basic | internal | auxiliary | development infrastructure exists | not a selected strong baseline |
| BM25 sparse retrieval | retrieval | internal | COMPLETE / auxiliary | frozen comparison evidence exists | not an independent reproduction target |
| TF-IDF retrieval | retrieval | internal | COMPLETE / auxiliary | frozen comparison evidence exists | not an independent reproduction target |
| PSE current | temporal structured retrieval | internal | COMPLETE / development | frozen normal/adversarial evidence exists | no formal parity claim |
| PSE candidate-v1 | temporal structured retrieval | internal frozen candidate | COMPLETE / development | leads v2 on normal frozen retrieval | weaker adversarial robustness than v2 |
| PSE candidate-v2 | temporal structured retrieval | internal frozen candidate | COMPLETE / development | stronger tested robustness; v4 MRR 0.875 | no formal universal selection; abstention unresolved |
| A-MEM | structured linked memory | `WujiangXu/A-mem` commit `0c8039f28fdcc08189a23c07a3437d9d2482f9c2` | D1/D2/D3 COMPLETE; D4 recovery active | exact frozen 24-case and adversarial-v4 evidence durably reproduced at USD 0 | complete 20-case recovered development retrieval, then frozen D4 end-to-end |
| TiMem | temporal-hierarchical | external source previously reviewed | not current primary target | source-level evidence only | exact compatible reproduction not completed |
| AgeMem | learned policy | external | blocked by present zero-cost resource boundary | source-level evidence only | training assets/GPU/resources |
| AgentRunbook-R/C | experience/query-time construction | external | not currently feasible at full scale | source-level evidence only | implementation/data/sandbox requirements |

## Primary strong-baseline target

```text
Primary method: exact-pinned A-MEM
Source commit: 0c8039f28fdcc08189a23c07a3437d9d2482f9c2
Zero-cost model path: qwen2.5:3b
D1: COMPLETE
D2: COMPLETE
D3: COMPLETE
D4: NOT COMPLETE
```

The original two-case-per-job frozen-development run `31284023872` was cancelled by its 180-minute execution timeout. Its artifacts contain no completed shard JSON and provide 0/20 formally salvageable cases.

Case-level recovery run `31292999631` uses the same frozen cases, source, model, embedding snapshot, dataset identity and scoring semantics, with one frozen case per job and a 350-minute timeout.

## Comparative claim boundary

Exact A-MEM adversarial-v4 run `31284978045` is complete. On 22 answerable cases A-MEM MRR is `0.833333` and PSE candidate-v2 MRR is `0.875`; the paired 95% bootstrap interval crosses zero. This is **UNDERPOWERED** and does not establish algorithm parity or superiority.

Abstention is also unresolved: both exact A-MEM and candidate-v2 false-retrieved on both v4 no-evidence cases.

## Current executable target

1. Complete and validate 20/20 case-level exact A-MEM frozen development retrieval.
2. Require zero missing / duplicate / invalid cases and valid artifact hashes/provenance.
3. Execute the frozen `experiments/protocols/amem-d4-development-v2.json` end-to-end run.
4. Preserve raw answers, raw evaluator outputs, resource evidence and artifact registry.
5. Recalculate Gate D only after the frozen acceptance contract passes.

No step above authorizes sealed-final, merge, release, parity, superiority, equivalence or non-inferiority claims.
