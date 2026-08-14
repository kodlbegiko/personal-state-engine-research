# Strong Baseline Failure Analysis

Current failure analysis is intentionally limited because the exact A-MEM retrieval runtime has not executed.

## Active blocker

The current isolated runner has 5 logical CPUs, 5.9 GiB RAM, no swap and no GPU. It does not have `sentence-transformers`, `transformers` or `rank-bm25` installed, and no `qwen2.5:3b` weights are present. The upstream source explicitly depends on those libraries and the robust zero-cost path uses Ollama.

## What is not counted as evidence

The mechanical adapter uses a fake upstream object in unit tests. No lexical, TF-IDF, BM25 or other substitute retriever is reported as A-MEM. Therefore retrieval misses, ranking misses, stale-memory failures and update conflicts remain unpopulated rather than fabricated.

## Next failure-analysis trigger

Populate the formal taxonomy only after:
1. exact-pinned A-MEM source is installed;
2. `all-MiniLM-L6-v2` is pinned and available;
3. Ollama `qwen2.5:3b` is pinned and reachable;
4. the 24-case synthetic corpus runs without changing its hash.
