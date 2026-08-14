# Strong Memory Baseline Landscape — 2026-08-08

## Decision

The deterministic 50-point rubric selects **A-MEM** as the Primary Strong Baseline and **TiMem** as the Secondary Strong Baseline.

| Candidate | Score / 50 | Key reason |
|---|---:|---|
| A-MEM | 45 | NeurIPS 2025, official reproduction repo, exact pin, compact source surface, official Ollama/vLLM path |
| TiMem | 44 | Findings of ACL 2026, direct LoCoMo + LongMemEval-S relevance, but materially heavier self-hosted stack |
| Mem0 | 42 | Direct modern benchmark tooling, but paper/managed optimizations are not a clean one-to-one OSS reproduction |
| MemoryOS | 40 | EMNLP 2025 Oral and strong personalization; heavier BGE-M3 + LLM runtime |
| Graphiti/Zep | 40 | Strong temporal graph design and LongMemEval evidence; graph DB + LLM stack increases reproduction burden |
| MemoryBank | 33 | Historically relevant personalization/update design, but weaker modern benchmark compatibility and original A100/OpenAI assumptions |
| LongMem | 25 | Scientifically strong long-context memory but weak fit to personal cross-session memory and current compute constraints |

The rubric is frozen before Primary execution. SHA-256: `4d9e2bfb90eb25b2ada93d669c0549e5c83b534263d97de70eca474442c8bb1b`.

## Why A-MEM

A-MEM creates structured memory notes with contextual descriptions, keywords and tags, links related memories, and supports memory evolution. The exact-pinned reproduction repository revision `0c8039f28fdcc08189a23c07a3437d9d2482f9c2` adds a robust pipeline that can use Ollama with `qwen2.5:3b`; retrieval is based on `all-MiniLM-L6-v2`. This provides a genuine zero-paid-API route without replacing the published memory algorithm.

## Why TiMem is Secondary

TiMem is newer and directly reports LoCoMo and LongMemEval-S, with a five-level Temporal Memory Tree and complexity-aware recall. It is therefore a scientifically important opponent. It is not Primary here because the self-hosted implementation brings PostgreSQL, Qdrant, LangGraph and LLM-service dependencies, materially reducing exact zero-cost reproduction feasibility on the current small CPU runner.

## Integrity boundary

- Simple BM25/vector/full-history methods remain basic baselines and are not counted as Gate D strong baselines.
- No candidate was selected after viewing PSE-vs-baseline outcomes.
- No sealed-final data was read.
- No paid API or cloud GPU was used.
- No retrieval metric is reported for A-MEM until the exact-pinned upstream embedding/LLM runtime actually executes.
