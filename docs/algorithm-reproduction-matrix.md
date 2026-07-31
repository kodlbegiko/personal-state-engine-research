# Algorithm Reproduction Matrix

Status date: 2026-07-31

No row in this table is a reproduction claim unless it is explicitly marked `OFFICIAL REPRODUCED`. Paper availability alone is insufficient.

| Method | Family | Official paper | Official code | License checked | Data checked | Resource fit | Status | Evidence gap |
|---|---|---:|---:|---:|---:|---:|---|---|
| B0 no cross-session memory | basic | N/A | internal | yes | internal only | feasible | ENVIRONMENT READY | real-model external run missing |
| Recent-history replay | basic | N/A | internal | yes | internal only | feasible | ENVIRONMENT READY | real-model external run missing |
| Rolling summary | basic | N/A | internal | yes | internal only | feasible | ENVIRONMENT READY | summary model and external run missing |
| Dense retrieval | retrieval | N/A | internal adapter incomplete | pending | external data missing | conditionally feasible | NOT STARTED | embedding model and index runner missing |
| BM25 sparse retrieval | retrieval | N/A | internal adapter incomplete | pending | external data missing | feasible | NOT STARTED | external adapter missing |
| Sparse-dense hybrid | retrieval | N/A | internal component exists | pending | external data missing | conditionally feasible | NOT STARTED | external real-model runner missing |
| TiMem | temporal-hierarchical | checked | repository located | pending compatibility review | benchmark data not local | constrained | SOURCE VERIFIED | exact commit, install, model config and official score reproduction missing |
| A-MEM | structured linked memory | checked | author code referenced | pending | benchmark data not local | constrained | SOURCE VERIFIED | exact commit, license and compatible evaluation setup missing |
| AgeMem | learned policy | checked | not yet verified | not checked | training assets unavailable | infeasible now | BLOCKED | official code, weights, training resources and GPU missing |
| AgentRunbook-R/C | experience and query-time construction | checked | not yet verified | not checked | LongMemEval-V2 not local | infeasible at full scale | SOURCE VERIFIED | official implementation, sandbox and data unavailable |
| PSE candidate | temporal structured memory | internal hypothesis | partial internal components | repository MIT | external data missing | conditionally feasible | NOT STARTED | no minimum external candidate implementation or E3 evidence |

## First executable target

```text
Benchmark: LongMemEval-S development subset
Methods: B0, recent history, rolling summary, BM25, dense and hybrid retrieval
Model: one pinned open-weight model
Evidence goal: E3 development-set results with raw outputs and complete manifests
```

## Blocking dependencies

1. External network path for benchmark and model downloads.
2. Dataset license and file-hash recording.
3. Pinned open-weight model runtime.
4. External benchmark adapter and evaluator.
5. Trial runner that records model, revision, prompt, request ID, cost and latency.
