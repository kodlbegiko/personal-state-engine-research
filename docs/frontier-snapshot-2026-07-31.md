# Frontier Snapshot — 2026-07-31

This document records the papers and official project sources checked during the first audit. It does not claim reproduction or independent validation.

## Benchmarks checked

- LoCoMo — arXiv:2402.17753; official repository: `snap-research/locomo`.
- LongMemEval — arXiv:2410.10813; official repository: `xiaowu0162/LongMemEval`.
- LongMemEval-V2 — arXiv:2605.12493.

## Method families checked

- TiMem — arXiv:2601.02845; temporal-hierarchical consolidation and complexity-aware recall.
- A-MEM — arXiv:2502.12110; linked structured memory and memory evolution.
- AgeMem — arXiv:2601.01885; learned unified short- and long-term memory policy.
- AdaMEM — arXiv:2606.05684; test-time adaptive trajectory and strategy memory.
- MGRetrieval — arXiv:2605.27437; reflective iterative retrieval.
- AgentRunbook-R and AgentRunbook-C — introduced with LongMemEval-V2.

## Initial selection

LongMemEval-S is the first adapter target because it has official data and evaluation code and is more feasible than LongMemEval-V2 under the current resource envelope. LoCoMo is the planned second external benchmark.

TiMem is the first structured and temporal strong-baseline candidate, subject to exact commit, license and execution verification. A-MEM is the secondary structured-memory candidate. AgeMem remains blocked for faithful reproduction until official implementation assets and sufficient training compute are available.

## Required verification before implementation claims

1. Record exact repository commits and licenses.
2. Download and hash the selected dataset.
3. Run the official evaluator against a known fixture.
4. Pin a real open-weight model and record its revision or file hash.
5. Do not reuse reported paper scores as repository results.
