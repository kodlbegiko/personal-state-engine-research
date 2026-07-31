# Contributing

## Principles

1. Preserve negative results and failed tests.
2. Do not alter final test data to improve scores.
3. Separate component regressions from model-efficacy claims.
4. Add a regression test for every bug fix.
5. Do not commit sensitive personal data or credentials.

## Local validation

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/run_benchmark.py
```

A contribution that changes benchmark behaviour must include:

- the reason for the change;
- affected scenarios and baselines;
- before-and-after raw results;
- an explanation of whether the change fixes a bug or changes the research construct.
