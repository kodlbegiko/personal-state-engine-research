# Limitations

1. The current benchmark is deterministic and component-level. It does not measure real LLM reliability.
2. Baseline implementations are simplified research adapters, not production implementations of commercial memory systems.
3. Similarity retrieval uses a local bag-of-words cosine proxy rather than embeddings.
4. The write policy is rule-based. The 23-case red-team corpus is small, curated by the same development process and vulnerable to adaptive attacks.
5. SQLite persistence is tested for separate-connection concurrent writes, schema integrity and compacted deletion, but multi-process load, migrations beyond schema v1, backups, replicas and embeddings remain untested.
6. Trusted-evidence mode validates source labels and digest format, not the authenticity of the observer or the semantics of arbitrary external effects.
7. The proactive threshold is hand-authored and has not been calibrated against user burden.
8. Every current pilot case has been observed; there is no untouched final set or stochastic model-run uncertainty.
9. Statistical outputs describe the fixed component cases only. They are not population inference and cannot establish model efficacy.
10. Provider-neutral adapters and trial records exist, but no external models, real-user data or independent human judges were used.
11. The local execution environment could not resolve `github.com`; repository writes use the authenticated GitHub connector.
12. A GitHub Release remains premature until model-backed evidence and independent reproduction are complete.
