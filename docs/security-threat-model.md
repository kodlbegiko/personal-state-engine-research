# Security Threat Model

Status date: 2026-07-31

## Protected assets

- user-scoped memories and provenance;
- current preference, state and commitment accuracy;
- deletion and retention guarantees;
- model and evaluator credentials;
- benchmark integrity and sealed-test confidentiality;
- experiment manifests, raw outputs and cost records.

## Trust boundaries

1. user input to memory-write policy;
2. model-generated content to durable storage;
3. external tool output to completion evidence;
4. one user or tenant to another;
5. primary memory to indexes, summaries, caches and derived memory;
6. repository code to downloaded datasets and model artifacts;
7. answer model output to evaluator or LLM judge.

## Primary threats and required controls

| Threat | Failure | Required control |
|---|---|---|
| memory injection | untrusted text becomes a durable instruction | content normalisation, conservative write policy, provenance and adversarial tests |
| provenance spoofing | forged sources receive trusted ranking | immutable source locators, trusted-source allowlists and hash validation where available |
| stale reinforcement | expired facts become stronger through repeated retrieval | temporal validity, supersession and harmful-retrieval tracking |
| malicious consolidation | poisoned records contaminate summaries or state | source-preserving consolidation, rollback and conflict checks |
| cross-user retrieval | one user's memory appears in another user's context | user-scoped storage and retrieval tests at every index layer |
| deletion leakage | deleted content remains accessible | propagation across records, indexes, summaries, caches and derived memory |
| sensitive-data overcapture | credentials or high-risk personal data are retained | secret detection, data minimisation and explicit permission rules |
| unauthorised update | model or tool changes a confirmed fact without authority | confirmation state, source reliability and update policy |
| false completion | tool self-report is treated as verified success | independent evidence, digest checks and recovery controls |
| benchmark tampering | data, baseline or evaluator changes without detection | locked execution boundary, source commit, dataset hash and append-only evidence |
| response mix-up | asynchronous or subprocess output is attached to the wrong request | strict request-identifier equality and manifest validation |
| judge bias | evaluator sees method identity or applies unstable rules | pinned judge, anonymisation, raw-output retention and human calibration |

## Security decision rules

- A safety test passing on a curated corpus is not a real-world coverage estimate.
- A memory algorithm cannot be declared at parity if a preregistered guardrail materially regresses.
- Secrets must never be printed in logs or committed, including during failure diagnosis.
- External code and model artifacts must be version-pinned and license-reviewed before execution.
- Security failures require a minimal reproducer and regression test; serious exploitable details should use a private GitHub security advisory rather than a public issue.

## Current evidence and gaps

The repository has automated tests for user isolation, secret and injection rejection, verified completion, recovery and deletion of implemented indexes. The 23-case write-policy corpus is only a small curated regression set. There is no external adversarial evaluation, no dense-vector deletion test, no full derived-memory deletion implementation and no real-model persistent-injection study. These gaps prevent a strong security claim.
