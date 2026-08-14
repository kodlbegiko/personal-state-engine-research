# Personal State Engine Pilot v0.3

Date: 2026-07-31

## Executive finding

The repository now demonstrates that a structured Personal State Engine can enforce a defined set of temporal, isolation, deletion, proactive, completion-verification and recovery invariants in deterministic software tests. It does **not** demonstrate that the architecture improves real language-model task success.

## Evidence delivered

- One clean research commit on `research/personal-state-engine-v0`
- Draft PR #2 against `main`
- 70 locally passing tests
- Python 3.11, 3.12 and 3.13 CI
- Nine component scenarios, eight baselines and 72 raw observations
- Frozen pilot hashes over benchmark, policy, scorer and runners
- SQLite persistence, schema/integrity checks, concurrent writers and tested plaintext deletion for implemented storage surfaces
- Trusted-evidence mode and rollback-gated recovery
- Provider-neutral model adapter and immutable trial-record schemas
- Independent structured scoring, Wilson intervals and exact paired comparison utilities
- A 23-case multilingual memory-write policy red team with benign controls

## Component results

B7 passes 9/9 fixed component cases, compared with 4/9 for B0. This gap is expected in part because B7 contains the specific capabilities the cases test. The paired B0-versus-B7 exact McNemar result is 0.0625 on nine fixed cases, but it is not an efficacy test, not a population estimate and not a substitute for repeated model runs.

## Safety pilot

The memory-write policy rejects 15/15 frozen injection-or-secret cases and accepts 8/8 benign controls. The corpus includes English, Traditional Chinese, Japanese, Korean, Unicode format-control obfuscation and several credential patterns. The result is corpus fit only; adaptive semantic attacks, encoding, provenance forgery and observer compromise remain open.

## Hypothesis verdicts

| Hypothesis | Pilot verdict |
|---|---|
| H1 Selective structured memory outperforms full replay | INCONCLUSIVE |
| H2 Temporal versioning reduces stale-memory errors | INCONCLUSIVE; deterministic invariant works |
| H3 Structured state outperforms rolling summary | INCONCLUSIVE |
| H4 Proactive intervention has net value | INCONCLUSIVE |
| H5 Verification reduces false completion | INCONCLUSIVE; deterministic rejection and recovery work |
| H6 Long context alone is insufficient | INCONCLUSIVE; finite-context simulation only |
| H7 Memory introduces privacy and persistence risks | PARTIALLY SUPPORTED at threat-model and test level |

## Blocking evidence

A final research verdict is blocked by the absence of:

1. a separately authored and untouched final benchmark;
2. repeated B0–B7 runs on at least two pinned models;
3. independent human or second-system adjudication;
4. realistic token, latency and monetary-cost evidence;
5. user-burden measurement for proactive intervention;
6. independent reproduction by another operator or implementation.

## Publication decision

Do not create a research tag or GitHub Release yet. Publishing this pilot as a final efficacy result would overstate the evidence. The Draft PR and raw files are the correct current publication state.
