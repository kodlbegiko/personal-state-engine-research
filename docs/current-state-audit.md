# Current State Audit

Audit timestamp: 2026-08-01T01:55:00+08:00

## Repository state

```yaml
auditor: OpenAI autonomous research agent
default_branch: main
working_branch: research/personal-state-engine-v0
pull_request: 2
pr_state: open
pr_draft: true
pr_mergeable: true
research_verdict: INCONCLUSIVE
highest_evidence: E3_PIPELINE_SMOKE
evidence_weighted_completion: 20_percent
```

The repository, branch, PR, issues, workflow jobs, raw evidence and committed files were inspected through the authenticated GitHub connector. README or progress claims were not accepted without checking workflow output and raw artifacts.

## Verified external evidence

The first real-model external smoke is durably committed in:

```text
results/external/first-e3-smoke/
```

Provenance:

```text
Evidence commit: 2728fc9fc11076db2be9418edea9520c8195b333
Source branch head: ca98c4789a7836651bde87f2d6b93fb140d737b0
Archive workflow run: 30652039317
Run ID: e3-smoke-30652039317-attempt-1
```

Confirmed facts:

- the pinned LongMemEval-S payload was downloaded and matched 277383467 bytes and SHA-256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`;
- 500 questions, 23867 sessions and 246750 turns passed structural validation;
- deterministic development, validation and sealed-final manifests were generated without cross-split history leakage;
- model and tokenizer revision `12fd25f77366fa6b3b4b768ec3050bf629380bac` were executed with q4 weights and Transformers.js 4.2.0;
- the q4 ONNX file SHA-256 is `933577110303a2964096d19b6f15d3b4639bef7f99481ac0b61d9f3ad72f392a`;
- four identical cases were executed under EXT-B0 and EXT-B5;
- all eight trials completed with no errors or timeouts;
- raw prompts, raw model outputs, retrieval records, token counts, latency, configuration hashes and request identifiers are committed;
- all 16 artifact-registry hashes tie to committed files;
- EXT-B0 records contain no history or retrieved items;
- EXT-B5 records contain one traceable retrieved session per case;
- no common API-key or bearer-token pattern was found in the evidence directory.

## Result interpretation

The provisional deterministic evaluator scored:

```text
EXT-B0: 0/4
EXT-B5: 0/4
```

This cannot establish equality, non-inferiority or method failure. The sample is deliberately small, the model is a 135M pipeline model, and the evaluator is not the official semantic evaluator.

The valid conclusion is:

```text
REAL-MODEL SMOKE — E3 PIPELINE EVIDENCE
Research verdict: INCONCLUSIVE
```

## Resource and dependency findings

The successful run used:

```yaml
runner: GitHub hosted ubuntu-24.04
cpu_count: 4
python: 3.11.15
node: 24.18.0
model_cache_bytes: 184178727
api_spend_usd: 0
```

The committed npm audit reports four high-severity dependency findings. They affect the isolated research runtime and prevent any security or production-readiness claim. No credential was used or committed.

## Remaining blockers

1. No predetermined 20–50-case development comparison exists.
2. No official or calibrated semantic evaluator is integrated.
3. EXT-B1–EXT-B4 and EXT-B6 have no real-model results.
4. No competitive pinned answer model has been evaluated.
5. No strong baseline has been faithfully reproduced.
6. PSE-Min has no external run or ablation.
7. No activated preregistration, sealed final test or independent reproduction exists.
8. Runtime dependency vulnerabilities remain unresolved.

## Publication decision

- keep PR #2 Draft;
- do not merge;
- do not tag or release;
- do not claim parity, superiority, validation, security or production readiness.
