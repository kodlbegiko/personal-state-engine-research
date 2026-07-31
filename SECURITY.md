# Security Policy

## Supported research branch

Security fixes currently target `research/personal-state-engine-v0` until the first reviewed merge to `main`.

## Reporting

Report vulnerabilities through a private GitHub security advisory when available. Do not publish credentials, personal data, or a working cross-user data-exfiltration payload in a public issue.

## Data handling rules

The repository must not contain:

- passwords, API keys, access tokens or private keys;
- identity documents or precise home addresses;
- private medical or financial records;
- raw private conversations without explicit consent;
- data that identifies minors in a sensitive context.

Synthetic data is the default. Any future real-user dataset requires explicit consent, minimisation, a retention schedule, a deletion procedure, and separation from the public repository.

## High-priority vulnerability classes

- cross-user memory retrieval;
- deletion that leaves retrievable copies;
- untrusted content persisted as durable instructions;
- provenance forgery;
- false completion with consequential side effects;
- autonomous high-risk action without confirmation.
