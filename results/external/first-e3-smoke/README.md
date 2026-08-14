# First E3 Real-Model Smoke Evidence

This directory archives the first real-model LongMemEval-S evidence produced by the Personal State Engine research branch.

```text
Research verdict: INCONCLUSIVE
Evidence level: E3 pipeline smoke
Evidence commit: 2728fc9fc11076db2be9418edea9520c8195b333
Source branch head: ca98c4789a7836651bde87f2d6b93fb140d737b0
Workflow run: 30652039317
Run ID: e3-smoke-30652039317-attempt-1
```

## Scope

The run executes four predetermined development-smoke cases under:

- `EXT-B0` — no cross-session memory;
- `EXT-B5` — deterministic BM25 retrieval with one selected session;
- `HuggingFaceTB/SmolLM2-135M-Instruct` at exact revision `12fd25f77366fa6b3b4b768ec3050bf629380bac`;
- q4 ONNX weights;
- Transformers.js 4.2.0 on a GitHub-hosted CPU runner.

All eight trials completed. The provisional deterministic evaluator scored both baselines 0/4. This is not evidence of parity, equivalence or method failure. The model is intended to establish a real-model evidence path, and the evaluator is not the official semantic evaluator.

## Contents

- `ARCHIVED.json` — archival provenance;
- `npm-audit.json` — dependency vulnerability evidence;
- `model-preload.*` — exact-model startup evidence;
- `e3-smoke-30652039317-attempt-1/dataset-audit.json`;
- deterministic split and smoke-selection manifests;
- model-cache and environment manifests;
- eight immutable raw trial records;
- processed summary;
- artifact registry with per-file SHA-256.

The 277 MB dataset and 184 MB model cache are not committed. Their revisions, sizes and hashes are recorded in the manifests.

## Known limitations

- four cases only;
- one small model;
- provisional evaluator;
- no official correctness score;
- no strong baseline;
- no PSE-Min run;
- no sealed evaluation;
- no independent reproduction;
- four high-severity npm audit findings in the isolated runtime dependency graph.
