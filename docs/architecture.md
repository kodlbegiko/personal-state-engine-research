# Architecture

## Data path

```text
source event
  -> memory write policy
  -> typed memory store
  -> temporal/version validation
  -> retrieval controller
  -> working context
  -> plan or intervention decision
  -> action
  -> trusted evidence verification
  -> rollback or alternative strategy when needed
  -> commitment and memory update
  -> immutable trial record and independent scoring
```

## Modules

### Memory models

`models.py` defines typed memory, provenance, temporal and commitment records. Each durable memory has a user identifier, key, source, confidence, status and validity interval.

### Write policy

`policy.py` enforces minimum durable-memory rules. It rejects empty content, invalid confidence, likely credentials, multilingual durable-instruction patterns, Unicode format-control obfuscation and model-inferred semantic facts presented as durable confirmed facts.

The pattern checks are a guardrail, not a complete injection detector. A frozen corpus with benign controls measures both missed attacks and false positives on the implemented cases.

### Store and version layer

`store.py` handles in-memory deduplication, supersession, user-scoped deletion and a plaintext-free audit digest.

`persistence.py` provides SQLite persistence with schema version metadata, integrity checks, busy timeouts, user-scoped records, temporal filtering, supersession, a derived search index, hash-only audit events and compacted deletion.

### Retrieval controller

`retrieval.py` combines semantic overlap, goal tags, project scope, source trust, recency and confidence. It applies user isolation, optional temporal filtering and a token budget.

### Commitment and proactive control

`commitments.py` implements explicit states and guarded transitions. `proactive.py` scores urgency, priority, expected loss, confidence and user burden, suppresses duplicate reminders and requires confirmation for higher-risk actions.

### Verification and recovery

`verification.py` distinguishes tool success from verified task completion. Strict mode requires evidence from a configured trusted observer and validates optional SHA-256 evidence digests.

`recovery.py` prevents an alternative action from running after an unverified side effect unless rollback is itself verified.

### Benchmark integrity, execution records and scoring

`benchmark_lock.py` freezes pilot data and evaluator hashes. `model_adapters.py` defines strict replay and subprocess interfaces. `experiment_records.py` validates model version, split, tokens, latency, status and unique trial IDs. `scoring.py` provides a scorer independent from the system under test, binary uncertainty summaries and exact paired comparisons.
