# LongMemEval official faithful-port v3 preparation

This directory records a non-destructive preparation pass for `longmemeval-official-faithful-port-v3`.

- Raw answer trials: 40/40, immutable integrity PASS.
- Official source: `9e0b455f4ef0e2ab8f2e582289761153549043fc` / `src/evaluation/evaluate_qa.py`.
- Official source SHA-256: `ecce9c4c79dc89d99534ac17b383a5cbb5b9f0c69ee98adaf0684742e3d95251`.
- Prompt and parser are fixed before any v3 judge execution.
- Existing evaluator v1 and v2 evidence is preserved.
- No answer model, BM25 retrieval, frozen case selection, sealed-final data or v3 judge inference was executed.
- Preparation verdict: **BLOCKED BY ENVIRONMENT**.
- Evaluator calibration: **NOT YET ESTABLISHED**.
- Formal v3 correctness use: **PROHIBITED**.
