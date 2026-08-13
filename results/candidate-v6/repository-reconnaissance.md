# Candidate-v6 Repository Reconnaissance

Status: PRE-IMPLEMENTATION RESEARCH EVIDENCE
Date: 2026-08-13
Candidate: candidate-v6
Method working name: Assertion-Structure Evidence Objects

## Operating context

- Repository: `kodlbegiko/personal-state-engine-research`
- Research branch: `research/personal-state-engine-v0`
- Starting HEAD: `6ba39b39eee407281a2376a356961ec9cda974a5`
- PR: #2
- PR state at reconnaissance: OPEN / DRAFT / NOT MERGED
- Gate A-D: COMPLETE
- Gate E: NOT COMPLETE
- Gate F: NOT STARTED; sealed-final remains prohibited
- Gate G: NOT COMPLETE
- Formal evidence-weighted completion: 45%
- Algorithm parity: NO
- Monetary cost policy: USD 0

## Candidate architecture map

### Candidate-v2

Frozen deterministic retrieval backend. It ranks memories using lexical similarity, recency, update bonuses, rare-anchor coverage, novel-token bonuses, echo penalties, and adversarial-cue penalties. Candidate-v6 should preserve this ranking whenever answerability verification succeeds.

### Candidate-v3

Adds a per-memory evidence-sufficiency filter on top of Candidate-v2. It detects relation concepts, uncertainty, question echo, and whether text has content beyond query/relation boilerplate. Weakness: value support is still inferred from residual lexical content rather than an explicit assertion object.

### Candidate-v4

Extends heuristic matching across attributes, subject anchors, context, temporal constraints, certainty, and value-token extraction. Weakness: it remains strongly heuristic and can over-abstain when evidence grammar diverges from expected token patterns.

### Candidate-v5

Frozen method identity: Atomic Requirement Evidence Graph. Candidate-v2 ranking is preserved when all query relation requirements receive compatible propositions; otherwise it abstains. Value-bearing evidence is still inferred by subtracting query/non-value stems from memory text. The protected validation isolated a structural failure: discourse/meta-text residue can survive subtraction and be misclassified as an answer value, producing both false contradictions and false support.

## Candidate-v5 frozen identity verification

Observed current source blob for `src/personal_state_engine/candidate_v5.py`:

`807e3fa41d42f67b2d751b99c77d3860d7c8a156`

This matches the previously recorded post-freeze git blob identity. The authoritative protected-validation summary records:

- candidate status: `REJECTED_BY_FROZEN_PROTECTED_VALIDATION_GUARDRAILS`
- freeze repository commit: `1fb360367668d5a5014b88d3f0f47f4b58cb2b43`
- freeze marker commit: `5a49c2157eb45acfc23fa65e6ce03dc666d3985d`
- source SHA-256: `f85be743db4d2658c90c5d2b8ec8dee0f0e1f4bdfe3e92066cbd2818c749d975`
- config SHA-256: `b0106d0560fae1e2a08a3107dda135d6f015ca3260a41d4daeed179da8e04e6a`
- changed after freeze: false
- formal protected validation run: `31665185021`
- rerun performed: false

Candidate-v5 is a closed research identity and is not an editable dependency of Candidate-v6.

## Reusable deterministic infrastructure

Candidate-v6 may reuse:

- Candidate-v2 retrieval function as a frozen ranking backend.
- Repository tokenizer/stemming/timestamp utilities.
- Existing deterministic metric and ranking evaluation helpers.
- Existing Candidate-v5 development-evidence workflow pattern.
- Existing benchmark hash/manifest conventions.
- Existing freeze and one-formal-execution workflow patterns, after adapting them to the new candidate identity.

## CI constraints

- Existing repository tests use `unittest`; Candidate-v6 tests must be discoverable and explicitly executed with `python -m unittest ... -v`.
- Development evidence must compile all Candidate-v6 surfaces, run unit/regression/property tests, materialize the deterministic development benchmark, verify its manifest/hash, enforce preregistered guardrails, verify a clean worktree, and upload immutable evidence.
- A failed development run is negative evidence, not a reason to delete or rewrite history.
- After freeze, source/config/selection thresholds are immutable.

## Benchmark-contamination controls

- Candidate-v5 protected validation is historical diagnostic evidence only.
- Its four known failures may guide mechanism formation but cannot become fresh Candidate-v6 confirmatory evidence.
- Historical failures included in development regression tests must be labeled `HISTORICAL_FAILURE_REGRESSION_ONLY`.
- Candidate-v6 protected validation labels/data must be generated only after Candidate-v6 freeze and frozen before one formal execution.
- No protected result may be used to tune Candidate-v6.

## Candidate-v6 allowed modification surfaces

Candidate-v6 work may create or modify only new Candidate-v6 surfaces and general CI/lock infrastructure when required for consistency, including:

- `src/personal_state_engine/candidate_v6.py`
- `tests/test_candidate_v6.py`
- `scripts/evaluate_candidate_v6.py`
- `benchmarks/algorithm-development/candidate-v6-development-v1/**`
- post-freeze `benchmarks/algorithm-development/candidate-v6-validation-v1/**`
- `experiments/configs/candidate-v6-v1.json`
- Candidate-v6 preregistration/protocol files
- Candidate-v6 CI workflows
- `results/candidate-v6/**`
- benchmark-lock files only through the repository's formal lock-regeneration process when required by new eligible files

## Frozen / forbidden surfaces

Candidate-v6 must not modify:

- Candidate-v5 source, config, frozen development data, protected validation data, or guardrails.
- Candidate-v4 frozen identity.
- Existing adversarial-v6 frozen data/results.
- Historical negative evidence.
- Any sealed-final content or metadata surface.

No sealed-final content/path operation was performed during this reconnaissance. The repository's previously recorded historical path-metadata integrity deviation remains preserved as historical evidence and is not re-inspected here.

## Research conclusion

A new candidate identity is justified. The next testable hypothesis is not another residual-token blacklist. Candidate-v6 should represent evidence as typed assertion objects and require an explicit value-bearing assertion slot before a memory can support an answer. Meta-discourse must be represented as a discourse role with no answer value.
