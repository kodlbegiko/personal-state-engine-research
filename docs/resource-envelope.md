# Resource Envelope

Assessment timestamp: 2026-07-31T18:04:00+08:00

## Confirmed local execution resources

```yaml
operating_system: Linux
python: 3.13.5
logical_cpu_count: 5
ram_total_gb: approximately 6.37
disk_free_gb: approximately 41.8
gpu: none detected
gpu_memory: 0
container_support: available for local Python and filesystem execution
git: available
github_cli: unavailable
ollama: unavailable
local_models: none detected
```

## Network and repository access

```yaml
direct_external_dns_from_container: failed
authenticated_github_connector: available
repository_read: available
repository_write: available
pull_request_and_issue_access: available
workflow_metadata_and_logs: available
github_actions_network: available for normal CI dependency installation
```

Direct DNS failure in the interactive container means local `git clone`, Hugging Face dataset download and model-weight download cannot be assumed. Repository work continued through the authenticated connector. GitHub Actions validated code and deterministic artifacts, but CI was not used to download the 277 MB benchmark or run a paid or unpinned model.

## Credentials and model runtimes

Only presence-state conclusions are retained; no secret value is recorded.

```yaml
openai_api_credentials: absent in inspected environment
anthropic_api_credentials: absent in inspected environment
google_or_gemini_credentials: absent in inspected environment
hugging_face_token: absent in inspected environment
ollama: absent
llama_cpp: untested_or_absent
mlx: untested_or_absent
vllm: absent
transformers: absent
pytorch: absent
onnx_runtime: absent
cuda: absent
mps: not applicable in Linux container
local_model_files: none detected
```

## Cost and execution limits

```yaml
paid_api_budget: 0 until credentials and an explicit ceiling exist
current_real_model_trials: 0
current_external_dataset_bytes_downloaded: 0
recommended_working_storage_ceiling_gb: 30
```

A paid or drifting API alias must not be used merely to obtain a quick score. The first model must have an exact provider identifier or local file hash, fixed runtime, tokenizer metadata, generation settings and a declared development-run cost ceiling.

## Selected execution lane

```text
Lane C — Blocked but Reproducible Setup
```

Engineering progress within Lane C now includes:

- pinned official LongMemEval-S source revision, size and SHA-256;
- checksum-verifying downloader and failure tests;
- integrated `EXT-B0` and `EXT-B5` trial entrypoint;
- immutable raw trial schema and collision protection;
- model/request attribution and classified failure retention;
- current-head CI across Python 3.11, 3.12 and 3.13.

Lane C still cannot produce E3 because no real dataset payload and no real model runtime are available in the same executable environment.

## Upgrade conditions

Move to Lane B only when all conditions are met:

1. the pinned LongMemEval-S payload is downloaded and its size and SHA-256 match the source manifest;
2. `scripts/validate_longmemeval.py` produces a committed dataset audit;
3. development, validation and untouched sealed-final split manifests are generated and leakage-checked;
4. one exact model and runtime are pinned and executable;
5. `EXT-B0` and `EXT-B5` smoke trials create raw immutable records with token, latency, failure and cost data.

Move to Lane A only after two external benchmarks, two pinned model versions, a faithfully reproduced strong baseline and sufficient compute are available for the preregistered matrix.
