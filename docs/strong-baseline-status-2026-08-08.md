# Gate D Strong-Baseline Mission Status — 2026-08-08

## Repository baseline

Starting research head: `381accff8677179b58a430a8e2a748e9d10127c1`.

The pre-existing rubric reports Gate A=10%, B=10%, C=10%, D=0%, E=0%, F=0%, G=0%, for 30% evidence-weighted completion. This mission does not invent sub-weights inside Gate D; until the repository defines numerical D1 credit or a faithful retrieval reproduction completes, the conservative numeric completion remains 30%.

## Strong baseline selection

- Primary: **A-MEM** — 45/50.
- Secondary: **TiMem** — 44/50.
- Selection frozen before any PSE-vs-primary result.
- Rubric SHA-256: `4d9e2bfb90eb25b2ada93d669c0549e5c83b534263d97de70eca474442c8bb1b`.
- Primary source commit: `0c8039f28fdcc08189a23c07a3437d9d2482f9c2`.
- Primary license: MIT.
- Secondary source commit: `6d279a5f5d40ee229e1995df15c182cb2062c71c`.

## Reproduction layers

| Layer | Status |
|---|---|
| D1 — source reproduction preparation | COMPLETE |
| D2 — memory algorithm execution | NOT COMPLETE |
| D3 — retrieval-level benchmark | NOT EXECUTED |
| D4 — end-to-end development reproduction | NOT EXECUTED |

Current verdict: **BLOCKED BY COMPUTE**.

The blocker is not a paid-API requirement: exact-pinned A-MEM provides an official Ollama `qwen2.5:3b` path. The current isolated runner has 5.9 GiB RAM, no GPU and does not already contain the necessary `sentence-transformers`/`transformers` stack or model weights. No replacement semantic algorithm is used to fabricate results.

## Engineering completed

- 24 independent synthetic cases, SHA-256 `6e8a66502752debb0c2385b5654bceb85a7a046a21c5bc7bea22ae1a460a61e9`.
- Mechanical upstream adapter that delegates semantics to exact A-MEM rather than reimplementing them.
- PSE-compatible retrieval metric reconstruction for Recall@1/3/5, MRR, nDCG@5 and irrelevant retrieval rate.
- Three deterministic unit checks, repeated three times: PASS.
- 20-artifact registry verifier: PASS.
- Dedicated Python 3.11/3.12/3.13 lightweight CI; a post-addition validation commit intentionally triggers it.
- Manual zero-cost A-MEM smoke workflow, pinned to the upstream commit and Ollama `qwen2.5:3b`; it is manual-only so standard CI does not download multi-GB model weights.

## Integrity boundaries

- Frozen 20-case development subset unchanged.
- Existing EXT-B0/EXT-B5 answers unchanged.
- No formal development pilot run before D2 prerequisites.
- No formal answer correctness attributed to A-MEM.
- No paid API used.
- No cloud GPU used.
- New monetary cost: USD 0.00.
- Sealed-final not accessed.
- PR #2 must remain Draft; no merge, tag or release.

## Progress accounting

```text
Previous research completion: 30%
Current research completion: 30% (conservative published rubric)
Change: 0 percentage points numerically
Gate D engineering state: D1 COMPLETE; D2/D3/D4 blocked/not executed
Remaining distance: 70%
Algorithm parity demonstrated: NO
```

The numeric percentage is intentionally not increased from source pinning/scaffolding alone because the existing repository does not assign an explicit partial percentage to D1.

## Next exact action

Run the manual zero-cost A-MEM smoke on an environment that can sustain `all-MiniLM-L6-v2` plus Ollama `qwen2.5:3b`. If the 24-case synthetic run passes, freeze the resolved dependency/model revisions and run the frozen development **retrieval** pilot before any answer-level claim.
