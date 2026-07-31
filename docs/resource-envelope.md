# Resource Envelope

Assessment timestamp: 2026-08-01T01:55:00+08:00

## Interactive execution environment

```yaml
operating_system: Linux
python: 3.13.5
logical_cpu_count: 5
ram_total_gb: approximately 6.37
disk_free_gb: approximately 41.8
gpu: none detected
github_cli: unavailable
direct_external_dns: unavailable
authenticated_github_connector: available
```

The interactive container still cannot directly download GitHub, Hugging Face datasets or model weights. Repository reads and writes remain available through the authenticated GitHub connector.

## Verified GitHub Actions execution lane

A network-enabled GitHub-hosted runner successfully executed the first E3 smoke:

```yaml
runner_image: ubuntu-24.04
cpu_count: 4
python: 3.11.15
node: 24.18.0
model_runtime: '@huggingface/transformers 4.2.0'
model: HuggingFaceTB/SmolLM2-135M-Instruct
model_revision: 12fd25f77366fa6b3b4b768ec3050bf629380bac
quantization: q4
model_cache_bytes: 184178727
dataset_bytes: 277383467
api_credentials_used: false
api_spend_usd: 0
```

The selected lane is now:

```text
Lane B — Networked open-weight external smoke execution
```

This lane supports small reproducible real-model experiments through a manual GitHub Actions workflow. It does not provide GPU acceleration, competitive model scale, independent reproduction or unrestricted experiment volume.

## Reproducibility controls

- exact dataset source revision, byte count and SHA-256;
- exact model and tokenizer revision;
- q4 ONNX weight hash recorded in the model-cache manifest;
- committed npm package-lock;
- manual workflow uses `npm ci`;
- raw requests, outputs, token use and latency committed;
- data and model payloads excluded from Git;
- no paid API calls;
- isolated ephemeral runner.

## Security limitation

The captured npm audit reports four high-severity vulnerabilities in the runtime dependency graph and no automatic fix. The current runtime is acceptable only as an isolated research smoke environment. It must not process untrusted archives or images and must not be described as secure or production ready.

## Practical execution ceiling

Under the current CPU-only lane:

- 4 paired cases are feasible and verified;
- EXT-B5 is substantially slower and more token-heavy than EXT-B0;
- a 20–50-case development run is technically possible but should use an explicit wall-clock and Actions-usage budget;
- larger or more capable models may exceed the available CPU runtime window;
- sealed-final testing is not authorized.

## Upgrade conditions

Before the next evidence tier:

1. select a more capable pinned model that remains within the declared compute budget;
2. integrate an official or calibrated semantic evaluator;
3. predefine a 20–50-case development subset;
4. resolve or isolate the high-severity runtime dependency findings;
5. complete the full basic external baseline matrix before PSE-Min expansion.
