# Zero-cost algorithm research status — 2026-08-08

## Verdict

`ZERO-COST ALGORITHM RESEARCH PARTIAL`

The zero-cost track now has a frozen synthetic benchmark extension, deterministic baseline ladder, current-PSE retrieval reconstruction, candidate v1, ablations, bootstrap intervals, robustness probes, regression tests, and CI-generated evidence. This work does not complete Gate D because exact-pinned A-MEM has not executed.

## Key retrieval evidence

| Split | System | MRR | nDCG@5 | Recall@1 | Recall@5 |
|---|---|---:|---:|---:|---:|
| Development (22 answerable) | PSE current reconstruction | 0.902 | 0.927 | 0.735 | 1.000 |
| Development | PSE candidate v1 | 1.000 | 1.000 | 0.917 | 1.000 |
| Validation (5 answerable) | PSE current reconstruction | 0.900 | 0.926 | 0.800 | 1.000 |
| Validation | PSE candidate v1 | 1.000 | 1.000 | 1.000 | 1.000 |
| Hidden-generated (6 answerable) | PSE current reconstruction | 0.833 | 0.877 | 0.472 | 1.000 |
| Hidden-generated | PSE candidate v1 | 0.917 | 0.938 | 0.639 | 1.000 |

The development candidate-current MRR delta is +0.0985 with a descriptive 95% bootstrap interval of [0.0227, 0.1970]. Validation and hidden-generated intervals include zero. Every comparison is marked `UNDERPOWERED`; these values do not establish general superiority.

## Ablation

The explicit update/state-transition bonus is the only candidate component with observed incremental value. The additional current-query recency term adds no observed value on these cases. Naive abstention and exact dedup variants were rejected because they create recall regressions.

## Robustness

Capitalization, punctuation, whitespace, reverse memory order, and missing timestamps did not change candidate MRR on the frozen development set. An irrelevant fresh duplicate reduced development MRR from 1.000 to 0.932. A lexical adversary that repeats the query reduced development MRR to 0.500 and hidden-generated MRR to 0.472. This is a material unresolved failure.

## Integrity boundary

- Original 24-case corpus unchanged and verified by SHA-256.
- Benchmark v2 extension frozen before candidate evaluation.
- 20 LongMemEval development cases and 40 raw EXT-B0/EXT-B5 answers were not changed.
- sealed-final was not accessed.
- paid API cost: USD 0.00.
- cloud GPU cost: USD 0.00.
- A-MEM: `NOT_EXECUTED`.
- Algorithm parity: `NO`.
- Formal repository completion remains 30% because the rubric does not assign partial percentage credit for this work.

## Gate D

```text
D1 = COMPLETE
D2 = NOT COMPLETE
D3 = NOT EXECUTED
D4 = NOT EXECUTED
A-MEM verdict = BLOCKED BY COMPUTE
```

The exact next evidence gate is still a successful zero-cost execution of exact-pinned A-MEM at commit `0c8039f28fdcc08189a23c07a3437d9d2482f9c2`, followed by the unchanged 24-case synthetic retrieval run.
