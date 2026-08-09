# Personal State Engine Research

A research prototype for testing whether structured, temporal, provenance-aware personal state management improves long-horizon AI-assistant reliability under fixed model, context, tool, token and cost constraints.

> **Current status:** exact-pinned A-MEM has been reproduced at retrieval level under a zero-monetary-cost path. D1/D2/D3 are complete; D4 end-to-end frozen development reproduction is not yet complete. The first frozen-development retrieval run timed out; a case-level zero-cost recovery is active. Candidate-v2 is descriptively competitive with exact A-MEM on the frozen adversarial-v4 benchmark, but the paired result is underpowered and abstention remains unresolved.

```text
Research verdict: INCONCLUSIVE
Evidence-weighted completion: 30%
Algorithm parity demonstrated: NO
Gate D: D1 COMPLETE / D2 COMPLETE / D3 COMPLETE / D4 NOT COMPLETE
Gate E: NOT COMPLETE
PR state: OPEN / DRAFT / NOT MERGED
New monetary cost: USD 0
Sealed-final content accessed: no
```

## Current external development evidence

- Dataset: LongMemEval-S cleaned
- Frozen development cases: 20, including 4 abstention cases
- Existing EXT-B0/EXT-B5 answer trials: 40 immutable records
- Answer model: `onnx-community/Qwen2.5-0.5B-Instruct`
- Answer-model revision: `956050e4c6ce7c647091e15311218f80d662559f`
- Evaluator v2: calibrated local fallback using official LongMemEval prompt semantics
- Evaluator calibration: raw agreement 95.0%, Cohen's kappa 0.7727, invalid-output rate 0.0%
- Formal development correctness use for evaluator v2: permitted within its development-only claim boundary
- Independent reproduction: false

The original EXT-B0/EXT-B5 development comparison remains underpowered: EXT-B0 scored 2/20 and EXT-B5 scored 4/20 under evaluator v2; exact McNemar two-sided p-value was 0.625. This does not establish improvement, parity, equivalence or non-inferiority.

## Strong baseline — exact A-MEM

Primary strong baseline: **A-MEM**.

```text
Upstream commit: 0c8039f28fdcc08189a23c07a3437d9d2482f9c2
Ollama model path: qwen2.5:3b
Paid API: false
Paid GPU: false
```

### Gate D state

| Layer | Status |
|---|---|
| D1 — source/protocol pin | COMPLETE |
| D2 — exact-pinned A-MEM execution | COMPLETE |
| D3 — frozen retrieval benchmark | COMPLETE |
| D4 — end-to-end frozen development reproduction | NOT COMPLETE |

The historical `BLOCKED BY COMPUTE` status is superseded for D2/D3. Exact A-MEM has executed successfully on GitHub-hosted zero-cost research runs.

### Frozen 24-case retrieval comparison

Durable A-MEM run: `31269598248`.

| System | MRR |
|---|---:|
| A-MEM exact | 0.878788 |
| PSE current reconstruction | 0.901515 |
| PSE candidate-v1 | 1.000000 |
| PSE candidate-v2 | 0.946970 |

This small frozen comparison is underpowered and is descriptive only.

## Adversarial-v4 exact A-MEM comparison

Exact A-MEM full-corpus workflow run `31284978045` completed successfully and durable outputs are stored under `results/strong-baseline/amem-adversarial-v4-full-v1/`.

The frozen v4 benchmark contains 24 total cases: 22 answerable and 2 no-evidence cases.

| System | MRR | Recall@1 | Recall@5 | Abstention accuracy |
|---|---:|---:|---:|---:|
| A-MEM exact | 0.833333 | 0.727273 | 1.000000 | 0.000 |
| PSE candidate-v2 | 0.875000 | 0.772727 | 1.000000 | 0.000 |

Paired candidate-v2 minus A-MEM MRR delta: `+0.041667`.

95% paired bootstrap CI: `[-0.109848, +0.196970]`.

Candidate-v2 versus A-MEM win/tie/loss: `5 / 12 / 5`.

Interpretation: **UNDERPOWERED**. The systems are descriptively competitive on this operator-designed adversarial benchmark, but the confidence interval crosses zero and n=22 is below the preregistered n=30 threshold. Formal parity, superiority, equivalence and non-inferiority are unsupported.

Both A-MEM and candidate-v2 false-retrieved on both v4 no-evidence cases.

## Candidate evidence

Candidate-v2 was frozen before the protected adversarial-v4 follow-up and was not retuned on v4 results. A completed 13-perturbation robustness suite shows substantially smaller degradation for v2 than current/v1 under the tested distractor stresses. Its worst observed perturbation was `duplicate_distractor_cluster`, at roughly -0.0909 MRR and Recall@1 from the v4 base.

Candidate-v1 still leads candidate-v2 on the normal frozen retrieval benchmark. Therefore there is currently **no formal universal candidate selection**.

## Abstention negative evidence

A development-only strategy matrix tested always-retrieve, absolute-score threshold, top1/top2 margin, evidence-coverage and combined-confidence strategies. Under the hard guardrail that answerable development queries cannot be falsely rejected, the safe configurations did not identify no-evidence cases:

```text
abstention accuracy = 0
false retrieval rate = 1
false abstention rate on answerable development = 0
```

This negative result is retained. Previously observed withheld data is not treated as hidden for further threshold tuning.

## Current D4 precursor — case-level recovery

Original A-MEM Frozen Development Retrieval run `31284023872` is **CANCELLED_BY_EXECUTION_TIMEOUT**. It passed Python 3.11, frozen split, dataset, source, Ollama and embedding checks, but all 10 two-case shard jobs hit the 180-minute execution timeout. All 10 artifacts were inspected and none contained a completed shard JSON, so formally salvageable cases = **0/20**.

Forensic evidence is stored under:

`results/strong-baseline/amem-development-recovery-v1/`

Active recovery workflow:

`.github/workflows/strong-baseline-amem-development-recovery.yml`

Active recovery run:

`31292999631`

Recovery preserves the same 20 frozen development cases / 4 abstention cases and all A-MEM/model/dataset/embedding identities. The existing runner is unchanged; execution is split into `shard-count = 20`, one frozen case per job, with a 350-minute timeout and max parallelism 10. Recovery dataset preparation and frozen split reproduction passed.

If and only if all 20 retrieval outputs complete and validate with no missing/duplicate/invalid cases, the next action is the preregistered end-to-end protocol `experiments/protocols/amem-d4-development-v2.json` through the repository's frozen D4 workflow.

## Current gate status

| Gate | Credit | Status |
|---|---:|---|
| A — repository, sources and licensing | 10 | COMPLETE |
| B — experiment infrastructure | 10 | COMPLETE |
| C — basic external baselines | 10 | COMPLETE |
| D — strong baseline reproduction | 0 | NOT COMPLETE; D1-D3 complete, D4 pending |
| E — PSE candidate | 0 | NOT COMPLETE |
| F — sealed parity test | 0 | NOT STARTED; sealed-final prohibited |
| G — independent reproduction | 0 | NOT COMPLETE |

```text
Evidence-weighted completion: 30%
Remaining formal distance: 70%
Algorithm parity demonstrated: NO
```

No partial Gate D or Gate E percentage is invented outside the repository rubric.

## Integrity and publication boundary

- Frozen development cases are unchanged.
- Existing immutable EXT-B0/EXT-B5 answers are unchanged.
- Frozen retrieval/adversarial benchmarks are not modified after observing results.
- Failed evaluator and negative abstention evidence remain preserved.
- No paid API or paid GPU is used for this continuation.
- Sealed-final content has not been accessed.
- PR #2 remains Draft / Open / Not merged.
- Do not merge, tag or release.
- Do not claim parity, superiority, equivalence, non-inferiority, validation, production readiness, security or state of the art.

See `docs/strong-baseline-status-2026-08-08.md`, `docs/zero-cost-algorithm-status-2026-08-08.md`, `results/continuation-mission/gate-e-assessment.json`, and the durable strong-baseline result directories for the current evidence boundary.

## License

MIT. Cite exact code, dataset, answer-model, evaluator and strong-baseline revisions together with the commit SHA.
