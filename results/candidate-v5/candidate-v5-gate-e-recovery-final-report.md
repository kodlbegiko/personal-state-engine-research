# Candidate-v5 Gate E Recovery — Final Report

## 1. Executive Verdict

**Candidate-v5 REJECTED.**

Candidate-v5 passed development guardrails and was formally frozen, but its single protected-validation execution failed the preregistered retrieval-preservation guardrails. The method remains frozen and must not be patched.

## 2. Formal Research Status

- Gate A: `COMPLETE`
- Gate B: `COMPLETE`
- Gate C: `COMPLETE`
- Gate D: `COMPLETE`
- Gate E: `NOT_COMPLETE`
- Gate F: `NOT_STARTED_SEALED_FINAL_PROHIBITED`
- Gate G: `NOT_COMPLETE`
- Formal completion: `45%`
- Algorithm parity: `NO`
- Candidate-v5: `FROZEN / REJECTED_BY_FROZEN_PROTECTED_VALIDATION_GUARDRAILS`
- PR #2: must remain `OPEN / DRAFT / NOT MERGED`
- Monetary cost: `USD 0`

## 3. Candidate-v5 Architecture

Candidate-v5 is a new method identity named **Atomic Requirement Evidence Graph**. It preserves Candidate-v2 as the frozen retrieval backend and separates retrieval relevance from answerability verification.

The verifier decomposes a query into mandatory requirements and requires conflict-free support across subject, predicate, value/object, temporal validity, completeness, contradiction state, unsupported-inference rejection, and query-echo resistance. Only a `SUPPORTED` verdict returns the original Candidate-v2 ranking; `INSUFFICIENT`, `CONTRADICTED`, or `AMBIGUOUS` returns `[]`.

Candidate-v5 is deterministic-only: no paid API, no paid GPU, and no local LLM verifier was used.

Frozen identity:

- Source SHA-256: `f85be743db4d2658c90c5d2b8ec8dee0f0e1f4bdfe3e92066cbd2818c749d975`
- Config SHA-256: `b0106d0560fae1e2a08a3107dda135d6f015ca3260a41d4daeed179da8e04e6a`
- Frozen repository state: `1fb360367668d5a5014b88d3f0f47f4b58cb2b43`
- Freeze marker commit: `5a49c2157eb45acfc23fa65e6ce03dc666d3985d`
- Freeze evidence run: `31664819435`
- Freeze evidence artifact: `9167515386`

## 4. Development Results

Development benchmark: 88 cases, 40 answerable and 48 no-evidence, SHA-256 `2a96ee9c15ff77dd359330e5bbf311a528f956041104f513045d39cfd966a93a`.

| Method | MRR | R@1 | R@3 | R@5 | Answerable recall | False abstention | No-evidence false retrieval | Abstention accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Candidate-v2 | 0.9000 | 0.7000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 |
| Candidate-v3 | 0.8250 | 0.6625 | 0.9125 | 0.9125 | 0.9250 | 0.0750 | 0.8750 | 0.1250 |
| Candidate-v4 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 |
| Candidate-v5 | 0.9000 | 0.7000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 1.0000 |

All frozen development guardrails passed. This evidence authorized freezing only; it did not authorize Gate E selection.

Development negative evidence was preserved. Two pre-freeze runs failed the query-echo unit test (`31664163704` and `31664231823`) before the deterministic parser repair. The final development run `31664329963` passed 16/16 unit tests and all 88 development cases.

## 5. Protected Validation

A new protected validation set was generated only after Candidate-v5 freeze and was frozen before execution:

- Total: 48
- Answerable: 24
- No-evidence: 24
- Dataset SHA-256: `9fe8b06b6a1ee051476171328e0cd330978fe996cdba8b6cfbf932cd23334af5`
- Formal execution count allowed: 1
- Formal run: `31665185021`
- Evidence artifact: `9167643375`
- Artifact SHA-256: `74372a54d173bb0bc74bfa848bfc01d2c260c7fc30d24d70fa07372db0f48ff3`
- Formal summary SHA-256: `5ad27259d7a9e2fea070807ebca7f23c15f7c53760206cf93989f3ec7de9c2fa`
- Evaluator exit code: `2`
- Rerun: `NO`

| Method | MRR | R@1 | R@3 | R@5 | Answerable recall | False abstention | No-evidence false retrieval | Abstention accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Candidate-v2 | 0.9167 | 0.7083 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 |
| Candidate-v3 | 0.8333 | 0.6667 | 0.8750 | 0.8750 | 0.9167 | 0.0833 | 0.9583 | 0.0417 |
| Candidate-v4 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 |
| Candidate-v5 | 0.8333 | 0.6250 | 0.9167 | 0.9167 | 0.9167 | 0.0833 | 0.0833 | 0.9167 |

Candidate-v5 passed the answerability and no-evidence safety thresholds but failed all four retrieval-preservation thresholds:

- MRR deficit vs v2: `0.08333` > allowed `0.03` → **FAIL**
- R@1 deficit: `0.08333` > allowed `0.03` → **FAIL**
- R@3 deficit: `0.08333` > allowed `0.02` → **FAIL**
- R@5 deficit: `0.08333` > allowed `0.02` → **FAIL**

The absolute no-evidence false-retrieval reduction vs Candidate-v2 was `0.91667`, exceeding the required `0.50`, but selection requires all critical guardrails to pass.

Observed failure cases:

- False abstention: `validation-a-013`, `validation-a-014` (`wrong_relation_distractor`).
- False retrieval: `validation-n-045`, `validation-n-046` (`high_overlap_no_value`).

Post-hoc diagnostic interpretation only: the remaining mechanism is **discourse/meta-text residue being misclassified as an answer value**. Agenda/review/question language can either create a spurious competing proposition and force abstention, or create false support where no value exists. This finding is not used to modify Candidate-v5.

## 6. adversarial-v7

`NOT_STARTED`.

Reason: protected validation is a required fresh prerequisite for Gate E. It failed frozen selection-critical guardrails, so Gate E cannot complete for Candidate-v5. Starting a new v7 confirmatory benchmark cannot legally cure or replace the failed protected validation and would not change the terminal Candidate-v5 decision.

No v7 generator, dataset, result, or post-result tuning was created.

## 7. Exact A-MEM Comparison

`NOT_REACHED_FOR_CANDIDATE_V5`.

The mission permits exact A-MEM only after a valid clean v7 discrimination stage. Because Candidate-v5 was rejected at protected validation, that condition was never reached. Existing historical A-MEM/v6 evidence remains historical and was not repurposed as Candidate-v5 confirmatory evidence.

## 8. Statistical Results

The immutable protected-validation predictions were analyzed without rerunning the benchmark:

- Candidate-v5 MRR: `0.83333`
- Candidate-v2 MRR: `0.91667`
- ΔMRR (v5 − v2): `-0.08333`
- Paired bootstrap: 10,000 repetitions
- Seed: `20260813`
- 95% CI: `[-0.20833, 0.00000]`
- Frozen noninferiority margin: `0.03`
- Noninferiority: **FAIL**
- Wins / ties / losses vs v2 on answerable reciprocal rank: `0 / 22 / 2`

Wilson 95% intervals:

- Candidate-v5 answerable recall 22/24 = `0.91667`, CI `[0.74151, 0.97684]`
- Candidate-v5 abstention accuracy 22/24 = `0.91667`, CI `[0.74151, 0.97684]`
- False-abstention rate 2/24 = `0.08333`, CI `[0.02316, 0.25849]`
- No-evidence false-retrieval rate 2/24 = `0.08333`, CI `[0.02316, 0.25849]`

These statistics confirm but do not create the rejection; the frozen guardrail failure was already terminal.

## 9. Integrity

- Candidate-v4 modified: `false`
- Candidate-v5 modified after freeze: `false`
- v6 modified: `false`
- v6 used as Candidate-v5 validation/confirmatory benchmark: `false`
- sealed-final accessed: `false`
- negative evidence deleted: `false`
- paid API: `false`
- paid GPU: `false`
- monetary cost: `USD 0`
- validation rerun: `false`
- validation benchmark edited after result: `false`

Preserved deviations/incidents include the two failed development unit-test runs and one pre-freeze evidence run that was not adopted because it verified pilot lock v0.11 instead of the formally regenerated v0.12. The formal freeze occurred only after the v0.12 identity was restored and independently reverified.

## 10. GitHub Evidence

Key commits / states:

- Repository reconnaissance: `7b88181d9eda042da5e13db072a3d066b8d09eca`
- v6 failure taxonomy: `ea83e5204cdc1824c14caa7141b6c3344a61d0f4`
- Hypothesis comparison: `b66df3063dfa726dc86e083b4e30568fc0c50be5`
- Candidate-v5 preregistration: `189af9eccbe55b7c739ebfaa6b8d75748b886ee8`
- Final pre-freeze Candidate-v5 implementation state: `99d01085d14d51b1f16c9383424564fb5272e9af`
- Formal Candidate-v5 frozen repository state: `1fb360367668d5a5014b88d3f0f47f4b58cb2b43`
- Freeze marker: `5a49c2157eb45acfc23fa65e6ce03dc666d3985d`
- Protected-validation materialization: `f468a4c744cf3654c3c77ea97352456653022d04`
- Protected-validation lock: `b21e7e4c69ea750180463733833630e1d72aef29`
- One formal protected-validation execution workflow commit: `e694ea641cd1f8fc8b712fac8006f85baa0400d6`
- Protected-validation failure record: `e7729aee6bef2a3de23f03f24392e08e3736de0c`
- Candidate-v6 direction record: `5a68f5a3d4487547750b81126d567b19e948b2f4`
- Protected-validation statistics: `ca6844e799a5d220631ed3cbd10a977b0332494d`

Key workflow evidence:

- Candidate-v5 development PASS: run `31664329963`, artifact `9167348416`
- Formal pilot-lock v0.12 regeneration: run `31664442549`, artifact `9167386489`
- Candidate-v5 freeze PASS: run `31664819435`, artifact `9167515386`
- Protected validation terminal FAIL: run `31665185021`, artifact `9167643375`

## 11. Gate Decision

`Gate E = NOT_COMPLETE`

The decisive failed condition is the fresh protected validation: Candidate-v5 violated frozen retrieval-preservation guardrails. Therefore Candidate-v5 cannot be formally selected and adversarial-v7 cannot repair this prerequisite.

Formal completion remains `45%`; work volume does not authorize increasing it.

Algorithm parity remains `NO` because no preregistered equivalence/parity test supports changing that status.

## 12. Next Action

Candidate-v5 must remain frozen and rejected.

The next method identity, if explicitly authorized in a future mission, should be **Candidate-v6 — Assertion-Structure Evidence Objects**. Its primary research target is replacing token-residue value detection with explicit assertion-role extraction so meta-discourse cannot create either false values or false contradictions.

Candidate-v6 must use a new preregistration, new source/config identity, new development set, and new protected evaluation. Candidate-v5 protected-validation cases may only be historical diagnostics for Candidate-v6; they must not become Candidate-v6 confirmatory selection data.

**Do not enter Gate F. sealed-final remains prohibited.**
