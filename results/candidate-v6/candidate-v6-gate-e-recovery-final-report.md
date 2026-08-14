# Candidate-v6 Gate E Recovery — Final Report

Date: 2026-08-13
Repository: `kodlbegiko/personal-state-engine-research`
Branch: `research/personal-state-engine-v0`
PR: #2
Candidate: `candidate-v6`
Method: **Assertion-Structure Evidence Objects**

## 1. Executive Verdict

Candidate-v6 **passes the scientific Gate E selection program** defined for this recovery mission:

- fresh post-freeze protected validation: PASS;
- protected-validation retrieval preservation: PASS;
- protected-validation answerability/no-evidence guardrails: PASS;
- protected-validation paired non-inferiority vs Candidate-v2: PASS;
- fresh adversarial-v7 benchmark discrimination: PASS;
- Candidate-v6 adversarial-v7 selection guardrails: PASS;
- exact-pinned A-MEM Stage 2: 90/90 valid;
- Candidate-v6 vs exact A-MEM paired MRR non-inferiority at margin 0.03: PASS.

Candidate-v6 is therefore **scientifically selected** and is not algorithmically rejected.

However, **formal repository Gate E remains NOT COMPLETE under fail-closed integrity policy**. The older frozen Gate E contract states that any recorded sealed-final listing/access deviation fails the formal Gate E integrity criterion even if payload content was not read. The repository contains the preserved historical `SEALED-PATH-METADATA-001` deviation from Candidate-v4. That deviation is metadata-only, did not expose sealed payload and was not used to design Candidate-v6, but the frozen rule does not permit treating it as cured.

Terminal state:

```text
CANDIDATE_V6 SCIENTIFIC_SELECTION: PASS
CANDIDATE_V6 ALGORITHMIC_REJECTION: NO
GATE_E SCIENTIFIC REQUIREMENTS: COMPLETE
GATE_E FORMAL: NOT COMPLETE — PREEXISTING FROZEN INTEGRITY CRITERION FAILS CLOSED
FORMAL EVIDENCE-WEIGHTED COMPLETION: 45%
FORMAL COMPLETION CHANGE: 0
ALGORITHM PARITY: NO
GATE_F: NOT STARTED — SEALED-FINAL PROHIBITED
PR: OPEN / DRAFT / NOT MERGED
NEW MONETARY COST: USD 0
NEW SEALED-FINAL ACCESS DURING CANDIDATE_V6 MISSION: NO
```

## 2. Starting State

At Candidate-v6 start:

- Gate A-D: COMPLETE
- Gate E: NOT COMPLETE
- Gate F: NOT STARTED / SEALED-FINAL PROHIBITED
- Gate G: NOT COMPLETE
- formal completion: 45%
- algorithm parity: NO
- Candidate-v5: FROZEN / REJECTED

Candidate-v5 source/config/protected validation were not modified or rerun.

## 3. Candidate-v5 Failure Mechanism

Candidate-v5 had already reduced no-evidence false retrieval substantially, but its protected validation isolated `discourse_residue_misclassified_as_answer_value`.

The structural issue was that Candidate-v5 could infer answer values from residual lexical material after subtracting query/non-value stems. Meta/discourse terms such as agenda/review/topic could therefore become fake value-bearing propositions, causing both false support and false contradictions.

Candidate-v6 was defined as a new method identity rather than a Candidate-v5 patch.

## 4. Candidate-v6 Architecture

Candidate-v6 uses a two-stage deterministic verifier:

1. **Discourse-role gate**
2. **Assertion-slot extractor**

A memory must first qualify as assertion-bearing text. Only then can it produce a typed evidence object with subject, predicate, object/value, polarity and temporal scope.

Meta-discussion, questions, agenda items, review topics, explicit no-value statements and unresolved/inferential text cannot create an answer value merely through lexical overlap.

Candidate-v2 remains the frozen retrieval backend. When Candidate-v6 returns `SUPPORTED`, Candidate-v2 ranking is preserved unchanged. Otherwise Candidate-v6 returns `[]`.

## 5. Architecture Hypotheses Considered

Pre-implementation comparison considered:

- rule-based assertion grammar only;
- deterministic proposition graph with typed discourse roles;
- two-stage discourse-role gate + assertion-slot extractor;
- token-sequence finite-state transducer with typed slots.

The two-stage parser was selected because it directly addresses the confirmed failure ordering: discourse role must be established before any object/value extraction occurs.

## 6. Preregistration

Preregistration was committed before formal implementation.

Key frozen selection thresholds included:

- MRR deficit vs Candidate-v2 <= 0.03
- R@1 deficit <= 0.03
- R@3/R@5 deficit <= 0.02
- answerable recall >= 0.95
- false abstention <= 0.05
- abstention accuracy >= 0.90
- no-evidence false retrieval <= 0.10
- absolute false-retrieval reduction vs Candidate-v2 >= 0.70
- assertion/meta/no-value/contradiction/temporal diagnostic accuracy >= 0.95 where deterministic ground truth exists
- paired-bootstrap MRR non-inferiority margin = 0.03
- bootstrap iterations = 10,000
- bootstrap seed = 20260813

Post-freeze source/config/threshold edits were prohibited.

## 7. Development Benchmark

`candidate-v6-development-v1`:

- 120 cases
- 50 answerable
- 70 no-evidence/adversarial
- dataset SHA-256: `393f669de845a4e3443273217d880d584035135643eaa933f6096b088b4cc25d`

Development evidence run:

- workflow run: `31688488856`
- job: `94410087985`
- artifact: `9176385585`
- artifact digest: `9b6155960ad6decbdc52930cd1703311f054db003c3914757bea54c694d8658d`

## 8. Development Results

33/33 Candidate-v6 unit/regression/metamorphic tests passed.

Candidate-v2 development metrics:

- MRR 0.76
- R@1 0.52
- R@3/R@5 1.00
- answerable recall 1.00
- false retrieval 1.00

Candidate-v6 development metrics:

- MRR 0.76
- R@1 0.52
- R@3/R@5 1.00
- answerable recall 1.00
- false abstention 0.00
- false retrieval 0.00
- abstention accuracy 1.00

All development retrieval deficits vs Candidate-v2 were zero. All registered parser diagnostic accuracies were 1.00.

Development evidence authorized freeze only.

## 9. Negative Evidence and Infrastructure Deviations

Negative/non-ideal evidence was preserved rather than deleted:

- new benchmark-lock-eligible Candidate-v6 executable files invalidated the existing pilot lock as expected;
- formal repository lock regeneration produced `pilot-v0.13`;
- the existing Zero-Cost Algorithm Evidence workflow still hard-coded `pilot-v0.11` and temporarily refreshed the version backward;
- this pre-freeze infrastructure inconsistency was repaired by aligning that workflow with `pilot-v0.13`;
- no Candidate-v6 source/config/threshold was changed by this repair.

The historical `SEALED-PATH-METADATA-001` integrity deviation was preserved and is decisive for the final formal Gate E boundary.

## 10. Freeze Identity

Candidate-v6 freeze repository commit:

`76cedf1ec533ba010aa0d992f436c19339c0d18d`

Freeze marker commit:

`af88deb300693e109ef22ec24e22ec3ec31efaad`

Frozen source SHA-256:

`c540056c6f30f0145ab8ef8c10be3abcae2ed24e6a087a2d9a3531bc5e545325`

Frozen config SHA-256:

`067bfa64d97bf2eb1f7208082c36d202118a0e50a2414fc345bf328f83cab5b1`

Freeze evidence:

- run `31688921031`
- job `94411460129`
- artifact `9176549407`
- artifact digest `32385e8345d71491406127b9adfe5d21d3a464c988c7e08bc611338c3ed84637`

Candidate-v6 source/config/selection thresholds were not modified after freeze.

## 11. Fresh Protected Validation

Fresh post-freeze benchmark:

- benchmark: `candidate-v6-validation-v1`
- 80 cases
- 40 answerable
- 40 no-evidence
- SHA-256: `855f812b3eec93f3229fe804ebd20e6e86baee5f99e9b322d11c114821215dc7`
- status before execution: `FROZEN_BEFORE_FORMAL_EXECUTION`
- formal execution count allowed: 1
- post-result editing: false

Formal execution:

- run `31689435267`
- job `94413075116`
- artifact `9176753372`
- artifact digest `55789c0536de28064ca02cba6c463b0df766ec1dca1738802fe28856d61d1e9a`
- rerun: NO
- verdict: PASS

## 12. Protected Validation Metrics

Candidate-v2:

- MRR 0.816667
- R@1 0.65
- R@3/R@5 1.00
- answerable recall 1.00
- false retrieval 1.00
- abstention accuracy 0.00

Candidate-v6:

- MRR 0.816667
- R@1 0.65
- R@3/R@5 1.00
- answerable recall 1.00
- false abstention 0.00
- false retrieval 0.00
- abstention accuracy 1.00

Retrieval deficits vs Candidate-v2 were all zero.

Assertion-specific checks computed from the same immutable one-time predictions:

- assertion extraction accuracy: 1.00
- meta-discourse rejection: 1.00
- explicit no-value detection: 1.00
- contradiction detection: 1.00
- temporal resolution: 1.00

## 13. Protected Validation Statistics

Candidate-v6 minus Candidate-v2 MRR:

- delta: 0.000000
- paired bootstrap iterations: 10,000
- seed: 20260813
- 95% CI: [0.000000, 0.000000]
- win/tie/loss: 0 / 40 / 0
- non-inferiority at margin 0.03: PASS

## 14. Fresh Adversarial-v7 Confirmatory Selection

A fresh 90-case benchmark was preregistered and frozen before any system execution:

- 60 answerable
- 30 no-evidence
- dataset SHA-256: `77f2113fdf67001c53a31f0d9eff4ecac7e71564335ab9a505665b44a05546cd`
- candidate-v6 development cases reused: NO
- candidate-v6 protected cases reused: NO
- candidate-v5 protected cases reused: NO

Stage-1 run `31689889393` passed.

Benchmark discrimination:

- Candidate-v2 MRR gap over max(random, recency): 0.523611
- Candidate-v2 R@1 gap over max(random, recency): 0.783333
- verdict: PASS

Candidate-v6 Stage-1:

- MRR/R@1/R@3/R@5: 1.00 / 1.00 / 1.00 / 1.00
- answerable recall: 1.00
- false abstention: 0.00
- false retrieval: 0.00
- abstention accuracy: 1.00
- all frozen selection guardrails: PASS

Exact A-MEM Stage-2 was therefore authorized.

## 15. Exact A-MEM Stage-2 and Frozen Statistics

Exact A-MEM identity:

- upstream commit: `0c8039f28fdcc08189a23c07a3437d9d2482f9c2`
- model: `qwen2.5:3b`
- Ollama digest: `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`
- embedding snapshot: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`

Stage-2 workflow:

- run: `31690210078`
- run attempt: 1
- conclusion: SUCCESS
- 30 shard artifacts + 1 final aggregate artifact
- final artifact: `9177810576`
- final ZIP digest: `af9508085a2554644085800850793f3fb87f2c94194cb6447208b820569d278f`

Acceptance:

- unique cases: 90
- missing: 0
- duplicate: 0
- invalid: 0
- status: 90/90 VALID

Candidate-v6:

- answerable MRR/R@1/R@3/R@5 = 1.00 / 1.00 / 1.00 / 1.00
- answerable recall = 1.00
- no-evidence false retrieval = 0/30 = 0.00
- abstention accuracy = 1.00

Exact A-MEM:

- answerable MRR/R@1/R@3/R@5 = 1.00 / 1.00 / 1.00 / 1.00
- answerable recall = 1.00
- no-evidence false retrieval = 30/30 = 1.00
- abstention accuracy = 0.00

Candidate-v6 vs exact A-MEM paired MRR statistics:

- answerable n = 60
- delta = 0.000000
- 10,000 bootstrap iterations
- seed = 20260813
- 95% CI = [0.000000, 0.000000]
- win/tie/loss = 0 / 60 / 0
- non-inferiority margin = 0.03
- non-inferiority = PASS
- superiority = NOT SUPPORTED

The 30/30 versus 0/30 no-evidence difference is a strong observed result on this frozen benchmark, but it is not reported as universal superiority.

## 16. Gate E Verdict

### Scientific Gate E

**COMPLETE / PASS for Candidate-v6.**

All Candidate-v6 scientific requirements in the preregistered adversarial-v7 protocol are satisfied:

- protected validation PASS;
- Stage-1 guardrails PASS;
- benchmark discrimination PASS;
- exact A-MEM 90/90 valid;
- frozen statistics executed;
- Candidate-v6 non-inferior to exact A-MEM on answerable MRR at the preregistered margin;
- no post-freeze Candidate-v6 patch;
- no post-result benchmark edit.

### Formal repository Gate E

**NOT COMPLETE — INTEGRITY FAIL-CLOSED.**

The pre-existing frozen Gate E contract (`adversarial-v6-confirmatory-evaluation-v1`) states that any recorded sealed-final listing/access deviation fails the formal integrity criterion even if content was not read.

The repository still contains the historical `SEALED-PATH-METADATA-001` deviation. Its preserved record states that a broad PR changed-filenames metadata query incidentally surfaced a path name containing a sealed-final marker; no sealed-final content was fetched/read/searched/inspected. The same record explicitly instructs final Gate E to apply fail-closed integrity rules.

Candidate-v6 did **not** cause or use this deviation, but the frozen formal contract does not permit erasing or curing it retroactively.

Therefore:

- scientific Candidate-v6 selection = PASS;
- Candidate-v6 algorithmic rejection = NO;
- formal Gate E selection authorization = NO;
- Gate E formal status = NOT COMPLETE;
- formal completion stays 45%.

## 17. Completion Percentage

Formal evidence-weighted completion remains **45%**.

No Gate E formal credit is awarded because the formal integrity criterion fails closed. Scientific progress is substantial, but the repository's own formal completion rubric cannot be inflated by ignoring a frozen integrity rule.

## 18. Algorithm Parity Status

**NO.**

The adversarial-v7 statistics protocol did not preregister an equivalence/parity test. Candidate-v6 and exact A-MEM have identical observed answerable MRR on v7 and Candidate-v6 satisfies the preregistered non-inferiority criterion, but non-inferiority is not equivalence.

## 19. Sealed-final Status

During the Candidate-v6 mission:

- new sealed-final content access: NO
- new sealed-final path operation: NO
- sealed-final payload used for design/tuning: NO
- Gate F entered: NO

Historical repository deviation:

- `SEALED-PATH-METADATA-001`: PRESENT
- payload content accessed: NO
- status: PRESERVED / NOT HIDDEN / NOT CURED

Gate F remains prohibited.

## 20. Cost

- new monetary cost: USD 0
- paid API: NO
- paid GPU: NO
- paid inference: NO

## 21. GitHub / PR Status

The mission did not merge, force-push, tag or release.

PR #2 must remain:

- OPEN
- DRAFT
- NOT MERGED

Final HEAD is recorded separately in the terminal snapshot after terminal evidence commits settle.

## 22. Integrity Ledger

Preserved material includes:

- Candidate-v5 protected-validation rejection;
- Candidate-v6 pre-freeze pilot-lock inconsistency and repair;
- historical Candidate-v4 validation exposure deviation;
- historical `SEALED-PATH-METADATA-001` metadata-only deviation;
- all frozen Candidate-v6 source/config identities;
- one-time protected-validation evidence;
- fresh adversarial-v7 frozen benchmark;
- exact A-MEM 30-shard / 90-case evidence;
- no post-result Candidate-v6 tuning.

Nothing above is represented as cured when it is not.

## 23. Next Legal Research Direction

Candidate-v6 itself does **not** require Candidate-v7 algorithmic replacement: its scientific selection passed.

The blocker is repository-level formal integrity lineage. Under the existing frozen Gate E contract, the historical path-metadata deviation cannot be retroactively cured inside this lineage.

The next legitimate research direction is therefore **a separately declared clean-integrity research track / clean repository lineage** that:

1. starts with an explicit new integrity contract before any protected or sealed surface exists;
2. imports only already-public/non-sealed frozen Candidate-v6 source identity and documented non-sealed evidence as permitted by that new protocol;
3. preserves provenance to this repository without claiming the historical deviation disappeared;
4. creates fresh confirmatory evidence under the clean lineage;
5. does not access the current repository's sealed-final surface;
6. does not reinterpret this repository's formal Gate E as complete.

This direction is recorded only. It is **not started** by this mission.
