# Model Adapter Protocol

## Purpose

The model-backed evaluation must not hard-code a single provider. `model_adapters.py` defines a provider-neutral request, response and run manifest, plus two concrete adapters:

- `ReplayAdapter` for deterministic reproduction of captured outputs;
- `SubprocessJSONAdapter` for an external provider runner communicating through one JSON request and response over standard input/output.

## Required manifest fields

- provider;
- model identifier;
- exact model version;
- temperature;
- seed when supported;
- token budget;
- timeout;
- fixed tool policy.

The adapter rejects incomplete manifests, malformed responses, missing replay records, non-zero subprocess exits and timeouts. It does not silently substitute a different model or fabricate a response.

## Current limitation

No real provider execution is included. The adapter and tests remove integration ambiguity, but Issue #1 remains open until repeated B0–B7 runs are executed against at least two pinned models with raw evidence.
