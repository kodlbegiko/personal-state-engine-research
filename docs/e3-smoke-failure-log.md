# First E3 Smoke Failure Log

## Attempt history

### Attempt 1 — dataset parser incompatibility

```text
Workflow run: 30650230782
Status: failed
Blocker class: DATASET_SCHEMA_COMPATIBILITY
```

The pinned LongMemEval-S payload downloaded and passed byte-count and SHA-256 validation. Parsing failed because the repository assumed `haystack_session_ids` were unique, while the official cleaned source contains repeated source labels in some cases.

Correction:

- preserve repeated source labels;
- disambiguate occurrences by timestamp and list position;
- do not rewrite or deduplicate source data;
- add a regression test based on the observed official shape.

### Attempt 2 — Node module-resolution failure

```text
Workflow run: 30650855850
Status: failed
Blocker class: RUNTIME_INTEGRATION
```

Dataset audit and split generation succeeded. The model server failed before readiness because the runtime package was installed under `experiments/runtime/node_modules`, while the ESM server lived under `scripts/` and could not resolve the package.

Correction:

- expose the exact runtime through a repository-root module link;
- add a model preload step that records stdout and stderr;
- keep the model, tokenizer, runtime and quantization pinned.

### Attempt 3 — successful E3 pipeline smoke

```text
Workflow run: 30651283901
Status: success
Evidence: Actions artifact and inspected raw records
```

A four-case paired EXT-B0/EXT-B5 smoke completed with eight successful real-model trials.

### Durable archival reproduction

```text
Workflow run: 30652039317
Status: success
Evidence commit: 2728fc9fc11076db2be9418edea9520c8195b333
```

The successful smoke was independently rerun in a second GitHub-hosted job and committed to the research branch with raw records, manifests, hashes and dependency audit.

## Interpretation

The failures are retained because they identify real incompatibilities in the data and runtime boundary. Neither failed attempt was counted as model-efficacy evidence. The successful run supports E3 pipeline evidence only.
