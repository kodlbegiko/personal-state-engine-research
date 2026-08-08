# Strong Baseline Reproduction Deviations

## Primary baseline

A-MEM, source commit `0c8039f28fdcc08189a23c07a3437d9d2482f9c2`.

## Current preparation

| Component | Classification | Status |
|---|---|---|
| paper/repository/commit/license pin | faithful | complete |
| upstream source-path mapping | faithful | complete |
| upstream requirements capture | faithful | complete |
| common PSE interface wrapper | mechanically-adapted | complete |
| 24-case synthetic corpus | mechanically-adapted evaluation infrastructure | complete |
| retrieval metric reconstruction | mechanically-adapted evaluation infrastructure | complete |
| `all-MiniLM-L6-v2` execution | resource-constrained | not executed |
| Ollama `qwen2.5:3b` memory evolution | resource-constrained | not executed |
| A-MEM semantic algorithm replacement | semantic deviation | **not performed** |

`AMemUpstreamAdapter` delegates semantic work to the upstream A-MEM object. Its unit tests use a fake object only to verify API mapping. Those tests must never be cited as A-MEM retrieval quality.

Because the exact embedding + LLM runtime did not execute in this environment, this preparation does **not** qualify as exact faithful A-MEM reproduction, retrieval-level reproduction, or end-to-end development reproduction.
