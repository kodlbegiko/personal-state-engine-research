# Failure Taxonomy

| Code | Definition | Example |
|---|---|---|
| `base_model_failure` | Model cannot perform the task despite correct state. | Invalid reasoning from accurate retrieved facts |
| `memory_write_failure` | Relevant information is not stored or unsafe information is stored. | Temporary event becomes permanent preference |
| `memory_update_failure` | New information does not correctly replace or qualify old information. | Cancelled plan remains active |
| `retrieval_failure` | Correct memory exists but is not selected. | Irrelevant semantic match outranks a project constraint |
| `temporal_reasoning_failure` | Validity, ordering or relative time is misapplied. | Expired schedule is used |
| `planning_failure` | State is correct but next action is wrong. | Ignores a dependency |
| `tool_failure` | External action fails or returns incomplete output. | File upload reports partial success |
| `verification_failure` | System marks completion without sufficient evidence. | HTTP 200 treated as user-visible success |
| `evaluation_failure` | Scoring or ground truth is wrong. | Judge rewards an unsafe reminder |
| `data_quality_failure` | Input data is ambiguous, duplicated or corrupted. | Two timestamps use different time zones |
| `privacy_failure` | Data is retained, exposed or mixed improperly. | User A receives User B's memory |
