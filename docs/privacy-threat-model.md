# Privacy and Security Threat Model

## Protected assets

- user-specific memories and commitments;
- provenance and consent metadata;
- deletion state;
- tool results and completion evidence;
- model and benchmark credentials used outside this repository.

## Trust boundaries

1. User input may be mistaken but is authoritative about preferences when explicitly confirmed.
2. External documents and websites are untrusted.
3. Model inference is not a confirmed user fact.
4. Tool success and tool self-report are not sufficient completion evidence.
5. Retrieval must enforce user identity before relevance scoring.
6. Statistical scoring code must be separate from the system being evaluated.

## Threats and controls

| Threat | Current control | Residual risk |
|---|---|---|
| Cross-user retrieval | User-scoped in-memory and SQLite stores; sequential and concurrent tests | No multi-process race or authorization-service integration |
| Prompt injection persistence | Unicode normalization, multilingual patterns, 23-case frozen corpus | Small curated corpus; adaptive and semantic attacks remain |
| Secret retention | Common API token, bearer, JWT and assignment-pattern rejection | Unknown formats, encoded secrets and false positives |
| Stale memory | Validity intervals and supersession | Incorrect timestamps or source updates |
| Deletion leakage | Tombstone, derived-index removal, secure-delete SQLite configuration and compaction test | Backups, replicas, embeddings and pre-deletion copies remain untested |
| Provenance forgery | Typed source metadata | No cryptographic attestation or identity binding |
| False completion | Effect checks, trusted evidence source option and digest validation | Trusted observer may be compromised; semantic effects remain hard to verify |
| Recovery side effects | Verified rollback before alternative action | Rollback may be incomplete outside observed state |
| Over-intervention | Threshold, burden and duplicate suppression | No real user-burden calibration |
| Evaluation leakage | Split labels and benchmark hashes | Current pilot cases have all been observed |

## Required future red-team work

- adaptive and encoded prompt injection;
- embedding index and backup erasure;
- provenance spoofing and observer compromise;
- gradual confidence escalation;
- adversarial reminder flooding;
- multi-process and multi-tenant race conditions;
- forged completion evidence with matching superficial effects;
- benchmark contamination and scorer gaming.
