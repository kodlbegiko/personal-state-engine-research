# Current PSE retrieval algorithm and zero-cost candidate v1

## Repository truth

The production research scaffold still routes `PersonalStateEngine.context()` through `RetrievalController`. The current retrieval controller enumerates temporally active memories, scores each record, sorts by score and observation time, and fills a token budget.

Current score in `src/personal_state_engine/retrieval.py`:

```text
0.45 * lexical cosine overlap
+ 0.15 * goal-tag match
+ 0.10 * project match
+ 0.12 * source trust
+ 0.10 * 30-day recency
+ 0.08 * confidence
```

The current implementation already has temporal validity through `MemoryRecord.is_valid_at()`, provenance weighting, exact duplicate handling in `MemoryStore`, and explicit `supersedes` state transitions. It does not include a semantic embedding model. Its constant provenance/confidence contribution can also make a zero-overlap record retrievable, so abstention is not solved by the current ranking rule.

## Benchmark reconstruction boundary

`pse_current_reconstruction` is a mechanical retrieval-only reconstruction for the frozen synthetic corpus. Synthetic records do not contain full PSE provenance/key fields, so the harness maps them to empty key, user-confirmed provenance, and confidence 1.0. Missing or malformed timestamps use the fixed benchmark reference time. This is a declared harness adaptation, not a claim of full end-to-end PSE execution.

## Candidate v1

Candidate v1 preserves the current reconstruction and adds two small deterministic signals:

1. `+0.18` for explicit state-transition/update cues in memory text (for example `updated`, `changed`, `stopped`, `corrected`, `revoked`).
2. `+0.04 * recency` for queries that explicitly ask for current/latest state.

The candidate does not inspect benchmark IDs, ground-truth labels, expected memory IDs, or split names. Benchmark v2 was frozen before candidate evaluation.

## Ablation interpretation

On the frozen synthetic evidence, removing the update bonus returns development MRR from 1.000 to the current reconstruction's 0.902; removing the query-recency term leaves MRR at 1.000. Therefore only the state-transition bonus has observed incremental value in this corpus. A naive abstention gate improved abstention but caused answerable recall regression, and exact deduplication reduced recall on duplicate-relevant cases; neither is promoted into candidate v1.

## Known limitations

- Candidate v1 does not solve abstention.
- It is highly vulnerable to a lexical adversary that copies the query text.
- The synthetic sample is small and all statistical comparisons remain underpowered.
- No A-MEM algorithm execution occurred, so no A-MEM parity or superiority claim is permitted.
- Candidate v1 is research-only and is not wired into the production `PersonalStateEngine` path.
