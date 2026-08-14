# Candidate-v6 Pre-Freeze Infrastructure Ledger

Date: 2026-08-13
Status: PRE-FREEZE / NON-SELECTION-CRITICAL

## Pilot lock interaction

Candidate-v6 introduced new benchmark-lock-eligible executable surfaces (`src/personal_state_engine/candidate_v6.py` and `scripts/evaluate_candidate_v6.py`). The repository authority `scripts/freeze_pilot_benchmark.py` requires a version bump when benchmark-affecting inputs change.

A formal regeneration workflow successfully created `pilot-v0.13` and anchor SHA-256 `acb43228a41caf4e9b001fa26cca0b73dee21ea43300babb8108cab1f35c8998`.

An existing `Zero-Cost Algorithm Evidence` workflow still hard-coded `pilot-v0.11`. On a later human-authored push it therefore refreshed only the lock version/anchor back to v0.11 in bot commit `55cedaa335cf1754733e4e74afe458cf0c1649fd`; Candidate-v6 source/config were not modified.

Classification: `PRE_FREEZE_INFRASTRUCTURE_CONSISTENCY_DEFECT`.

Repair: update only `.github/workflows/zero-cost-algorithm-evidence.yml` so its authoritative refresh invokes `python scripts/freeze_pilot_benchmark.py --version pilot-v0.13`. Commit: `2c2c5fd4dbbb6bdf83faa7509b1bc974cd436b32`.

The repaired workflow re-ran repository tests, lock generation/verification, deterministic zero-cost evidence, and integrity checks successfully. It restored the formally intended `pilot-v0.13` lock in bot commit `99a40162d8b3c8a068b210d577b11640a7dae74b`.

This repair occurred before Candidate-v6 freeze and changed no Candidate-v6 algorithm source, config, preregistered threshold, development dataset, or development result.

## Preserved negative / non-ideal evidence

- CI run `31688618936` on the pre-regeneration workflow commit failed while the lock had not yet been regenerated; this is preserved as infrastructure evidence.
- Bot commit `55cedaa335cf1754733e4e74afe458cf0c1649fd` temporarily reverted the lock version to v0.11 due to the stale workflow constant; it is preserved in history.
- No failed evidence was deleted or rewritten.

## Integrity boundary

- Candidate-v6 source modified by this repair: NO
- Candidate-v6 config modified by this repair: NO
- Selection thresholds changed: NO
- Candidate-v5 modified: NO
- Protected validation observed: NO (not created yet)
- New sealed-final access: NO
- Monetary cost: USD 0
- Paid API/GPU/inference: NO
