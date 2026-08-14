# Research Plan

## Objective

Evaluate whether structured personal state improves reliable cross-session assistance relative to no memory, full-history replay, rolling summaries, and similarity-only retrieval.

## Primary hypotheses

The preregistered hypotheses are listed in `hypotheses.md`. The current implementation is an engineering pilot and may be modified before the final model-backed benchmark is frozen. Once a final test set is frozen, changes to it require a new benchmark version.

## Experimental phases

### Phase 1 — Component validity

- Define state schemas and invariants.
- Test temporal validity, provenance, deletion and user isolation.
- Build deterministic B0–B7 adapters.
- Establish regression tests.

### Phase 2 — Model-backed controlled evaluation

- Freeze development, validation and final test partitions.
- Select at least two base models and pin exact versions.
- Hold prompts, tools, token budgets and temperature constant where possible.
- Run repeated independent trials with fixed and varied seeds.
- Save all raw outputs, failures, costs and latency.

### Phase 3 — Long-horizon simulation

- Simulate weeks or months of updates, cancellations, conflicts and commitments.
- Measure stale-memory use, repeated failure and false completion.
- Stress-test memory consolidation and deletion.

### Phase 4 — Consented user evaluation

Only proceed if synthetic and semi-synthetic evidence justifies human testing. Use explicit consent, data minimisation, withdrawal and deletion procedures.

## Primary outcomes

- task success rate;
- stale-memory usage rate;
- false-completion rate;
- cross-user leakage rate;
- intervention precision and unnecessary interruption rate;
- cost per successful task.

## Non-negotiable controls

- no self-evaluation as the sole judge;
- no deletion of negative runs;
- no final-set tuning;
- no unequal token budget without disclosure;
- no claim of product readiness from component tests alone.
