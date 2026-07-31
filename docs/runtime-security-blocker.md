# External Smoke Runtime Security Blocker

The first real-model smoke used an isolated GitHub-hosted runner and captured an exact npm dependency graph.

The committed audit reports four high-severity findings:

- direct package: `@huggingface/transformers`;
- transitive runtime: `onnxruntime-node` through vulnerable `adm-zip`;
- transitive image runtime: `sharp` through inherited `libvips` findings;
- `npm audit` reported no automatic fix for the captured graph.

Evidence:

```text
results/external/first-e3-smoke/npm-audit.json
experiments/runtime/package-lock.json
```

Impact:

- the runtime must remain isolated and research-only;
- it must not process untrusted archives or images;
- the repository must not claim the runtime is secure or production ready;
- the E3 model-output evidence remains valid as pipeline evidence, but runtime risk must be disclosed.

Acceptance criteria:

1. upgrade to a pinned runtime graph with no known high or critical findings, or document a narrowly scoped mitigation supported by evidence;
2. rerun the exact-model smoke after the runtime change;
3. preserve before/after package-lock and audit outputs;
4. verify raw-result compatibility and note any numerical drift.
