# Data Governance

Status date: 2026-07-31

## Permitted research data

Use only:

- legally public data with recorded terms;
- benchmark data whose license permits the intended research and publication;
- synthetic or de-identified fixtures;
- explicitly consented data handled under a documented retention and deletion process.

Private conversations, credentials, identity documents, precise addresses, medical records, financial records and sensitive information about minors must not be committed to this repository.

## Dataset intake record

Before using an external dataset, record:

```text
source URL or repository
owner or publisher
license and version
retrieval date
dataset version
original file names
cryptographic hashes
transform scripts
transformed file hashes
intended split role
known contamination risk
redistribution restrictions
```

A transformed, filtered, translated or repaired dataset must receive a distinct name and dataset card. It must not be reported as directly identical to the official release.

## Data minimisation

- Store only fields required by the research question.
- Do not preserve raw secrets in logs, error messages or model traces.
- Use synthetic identifiers in public artifacts.
- Separate user identity mappings from benchmark records.
- Do not retain assistant-derived sensitive inferences unless the experiment explicitly requires and authorises them.

## Split and access governance

Each dataset must be labelled as one of:

```text
DEVELOPMENT
VALIDATION
SEALED FINAL TEST
EXTERNAL COMPARABILITY ONLY
ROBUSTNESS_OR_REGRESSION
```

Access to a sealed final test must be recorded. Once a developer views its cases or uses its errors for tuning, it is contaminated and cannot support the same confirmatory claim.

## Raw outputs

Raw experiment outputs must use unique run identifiers and must not be overwritten. Before committing or publishing them:

1. scan for credentials and personal data;
2. verify dataset redistribution rights;
3. preserve model and evaluator identifiers;
4. retain parse failures and unsuccessful runs;
5. redact secrets without altering scores or hiding failures.

## Retention and deletion

Deletion must propagate through:

- primary records;
- sparse and dense indexes;
- summaries and consolidated memories;
- caches;
- derived records;
- exported artifacts under project control.

A deletion claim is unsupported until residual retrieval and plaintext checks pass. Backups outside project control must be documented rather than silently treated as deleted.

## Current repository status

The current committed benchmark materials are synthetic or curated fixtures. No external LongMemEval or LoCoMo dataset is committed. No dataset license or official data hash has yet been recorded, so external Benchmark execution remains blocked.
