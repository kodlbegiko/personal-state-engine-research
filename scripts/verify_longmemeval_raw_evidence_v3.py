from __future__ import annotations

import json
import tempfile
from pathlib import Path

from prepare_longmemeval_faithful_port import prepare

EXPECTED = {
    "case_id_sha256": "519b4db13813b60ad6a49cce919543b0639524a98bd1b0d1615c53e62cf8cc7e",
    "ordered_answer_set_sha256": "a7bcd93c9fb24e0b22e3a48c8ba0f181ac41927bfde1e2af119e05ef083f25ab",
    "unordered_answer_multiset_sha256": "686c7b2ae60ace9c4636ca228c4c0c6be055112325386a79daa27302ab3e4b6e",
    "raw_trial_set_sha256": "401417eeae4151e80057a8b28fbf81942e779735a0e27bade334e0489839c886",
}


def main() -> int:
    repo_root = Path.cwd().resolve()
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "preparation"
        prepare(repo_root, output)
        report = json.loads((output / "raw-evidence-integrity.json").read_text(encoding="utf-8"))
    required = {
        "expected_raw_trials": 40,
        "observed_raw_trials": 40,
        "case_count": 20,
        "case_pairs_complete": True,
        "trial_ids_unique": True,
        "request_ids_unique": True,
        "ext_b0_cross_session_history_absent": True,
        "ext_b5_retrieval_trace_present": True,
        "answer_model_rerun": False,
        "sealed_final_accessed": False,
        "integrity_verdict": "PASS",
    }
    for key, value in required.items():
        if report.get(key) != value:
            raise SystemExit(f"raw evidence check failed: {key}={report.get(key)!r}, expected {value!r}")
    for key, value in EXPECTED.items():
        if report.get(key) != value:
            raise SystemExit(f"raw evidence hash mismatch: {key}")
    archive = report.get("archive_registry", {})
    if archive.get("status") != "PASS" or archive.get("artifact_count") != 59 or archive.get("registered_artifact_sha256_checks") != 59:
        raise SystemExit("archive registry did not verify 59/59 artifacts")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
