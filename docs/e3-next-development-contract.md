# Next E3 Development Contract

The next experiment must not reuse the four-case smoke sample as the full development result.

Minimum next matrix:

```text
LongMemEval-S predetermined development subset: 20–50 cases
Model: one more capable exact pinned revision
Baselines: EXT-B0 and EXT-B5 on identical case IDs
Evaluator: official or calibrated semantic evaluator
Raw trials: all successes, errors, timeouts and invalid outputs retained
```

Fixed before execution:

- case IDs and split hash;
- model and tokenizer revision;
- runtime and package-lock;
- BM25 document unit, query, k, tie-breaking and budget;
- generation parameters;
- timeout and retry rules;
- primary and secondary metrics;
- evaluation prompt and version;
- lifecycle token, latency, storage and compute accounting.

The next run may tune development configurations only by creating a new config version and run ID. Existing E3 smoke outputs must not be overwritten.

PSE-Min, TiMem and additional complex memory modules remain out of scope until this basic paired development matrix is stable.
