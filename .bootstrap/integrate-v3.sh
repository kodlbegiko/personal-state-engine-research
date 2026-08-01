#!/usr/bin/env bash
set -euo pipefail

cat .bootstrap/pse-v3-bundle.part{00..07} > /tmp/pse-v3-bundle.b64
base64 --decode /tmp/pse-v3-bundle.b64 > /tmp/pse-v3-bundle.zip
echo '0945d2e5140ae738bc4821d9db00def67c62a963cc0af116f0c6eff20cffe9d9  /tmp/pse-v3-bundle.zip' | sha256sum -c -
python - <<'PY'
from pathlib import Path, PurePosixPath
import stat
import zipfile

archive = Path('/tmp/pse-v3-bundle.zip')
target = Path('/tmp/pse-v3-bundle')
target.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(archive) as zf:
    for info in zf.infolist():
        path = PurePosixPath(info.filename)
        mode = info.external_attr >> 16
        if path.is_absolute() or '..' in path.parts:
            raise SystemExit(f'unsafe ZIP path: {info.filename}')
        if stat.S_ISLNK(mode):
            raise SystemExit(f'symlink prohibited: {info.filename}')
    zf.extractall(target)
PY

python -m pip install -e .
cp -R /tmp/pse-v3-bundle/. .

python - <<'PY'
from pathlib import Path

prepare = Path('scripts/prepare_longmemeval_faithful_port.py')
text = prepare.read_text(encoding='utf-8')
old = 'OUTPUT_DIRECTORY = "results/external/longmemeval-evaluator-v3-preparation"'
new = 'OUTPUT_DIRECTORY = "results/external/longmemeval-faithful-port-v3-preparation"'
if text.count(old) != 1:
    raise SystemExit('unexpected output-directory definition')
text = text.replace(old, new)

lines = text.splitlines()
in_model_selection = False
changed = False
for index, line in enumerate(lines):
    if '"component": "model selection"' in line:
        in_model_selection = True
    elif in_model_selection and '"effect_on_semantics": "none"' in line:
        lines[index] = line.replace('"none"', '"potential"')
        changed = True
        break
if not changed:
    raise SystemExit('model-selection semantic deviation was not found')
text = '\n'.join(lines) + '\n'

old = 'verdict = "READY FOR BLINDED CALIBRATION" if exact_runtime_available else "BLOCKED BY ENVIRONMENT"'
new = 'verdict = "READY FOR FRESH BLINDED CALIBRATION" if exact_runtime_available else "BLOCKED BY ENVIRONMENT"'
if text.count(old) != 1:
    raise SystemExit('unexpected preparation verdict expression')
text = text.replace(old, new)

anchor = '    write_json(output_root / "official-source-manifest.json", source_manifest)\n'
addition = anchor + '    _write_text(output_root / "official-source-snapshot.sha256", OFFICIAL_SOURCE_SHA256 + "\\n")\n'
if text.count(anchor) != 1:
    raise SystemExit('official source write anchor not found')
text = text.replace(anchor, addition)
prepare.write_text(text, encoding='utf-8')

verifier = Path('scripts/verify_longmemeval_faithful_port_preparation.py')
text = verifier.read_text(encoding='utf-8')
anchor = '    "official-source-manifest.json",\n'
addition = anchor + '    "official-source-snapshot.sha256",\n'
if text.count(anchor) != 1:
    raise SystemExit('verifier expected-file anchor not found')
text = text.replace(anchor, addition)
old = '{"READY FOR BLINDED CALIBRATION", "BLOCKED BY ENVIRONMENT"}'
new = '{"READY FOR FRESH BLINDED CALIBRATION", "BLOCKED BY ENVIRONMENT"}'
if text.count(old) != 1:
    raise SystemExit('verifier verdict enum not found')
text = text.replace(old, new)
anchor = '    evaluator = _load_json(output_root / "evaluator-manifest.json")\n'
addition = (
    '    snapshot_hash = (output_root / "official-source-snapshot.sha256").read_text(encoding="utf-8").strip()\n'
    '    if snapshot_hash != OFFICIAL_SOURCE_SHA256:\n'
    '        raise ValueError("official source snapshot hash mismatch")\n\n'
    + anchor
)
if text.count(anchor) != 1:
    raise SystemExit('verifier source-hash anchor not found')
text = text.replace(anchor, addition)
verifier.write_text(text, encoding='utf-8')
PY

cat > scripts/verify_longmemeval_raw_evidence_v3.py <<'PY'
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
PY

python -m compileall -q src scripts tests experiments/runners
python -m unittest discover -s tests -v
python scripts/verify_longmemeval_raw_evidence_v3.py
python scripts/prepare_longmemeval_faithful_port.py
python scripts/verify_longmemeval_faithful_port_preparation.py

output='results/external/longmemeval-faithful-port-v3-preparation'
test ! -e "$output/formal-rescoring.jsonl"
test ! -e "$output/formal-summary.json"
test ! -e "$output/paired-analysis.json"
if find "$output" -type f \( -name '*.bin' -o -name '*.gguf' -o -name '*.onnx' -o -name '*.safetensors' -o -name '*.pt' -o -name '*.pth' \) | grep -q .; then
  echo 'model or dataset payload detected' >&2
  exit 1
fi
if grep -R -n -E 'sk-proj-|sk-live-|OPENAI_API_KEY=' "$output"; then
  echo 'secret marker detected' >&2
  exit 1
fi
if grep -R -n -E 'longmemeval-s-sealed_final|sealed[-_ ]final.*payload' "$output"; then
  echo 'sealed-final payload reference detected' >&2
  exit 1
fi

python - <<'PY'
from pathlib import Path

marker = '<!-- longmemeval-faithful-port-v3-preparation -->'
block = '''

<!-- longmemeval-faithful-port-v3-preparation -->
## LongMemEval faithful-port v3 preparation

The repository now contains an independent official-source faithful-port v3 preparation. It preserves evaluator v1/v2 evidence, re-verifies the immutable 40-answer development matrix and all 59 archived artifacts, uses a strict JSON parser, identity-free deterministic blinding, and a separate 24-case synthetic corpus.

```text
Evaluator: longmemeval-official-faithful-port-v3
Source type: faithful-port
Official runtime: BLOCKED BY ENVIRONMENT
v3 calibration: NOT YET ESTABLISHED
v3 formal correctness use: PROHIBITED
Research completion: 30%
Sealed-final accessed: false
```
'''.rstrip() + '\n'
for name in ('README.md', 'docs/progress.md'):
    path = Path(name)
    text = path.read_text(encoding='utf-8')
    if marker not in text:
        path.write_text(text.rstrip() + block, encoding='utf-8')
PY

git rm .bootstrap/pse-v3-bundle.part{00..07} .bootstrap/integrate-v3.sh
git add \
  src/personal_state_engine/longmemeval_faithful_port.py \
  scripts/prepare_longmemeval_faithful_port.py \
  scripts/verify_longmemeval_faithful_port_preparation.py \
  scripts/verify_longmemeval_raw_evidence_v3.py \
  tests/test_longmemeval_faithful_port.py \
  benchmarks/evaluator/longmemeval-faithful-port-unit-v3.json \
  experiments/evaluators/longmemeval-official-faithful-port-v3.json \
  references/longmemeval-official-evaluator-source-v3.json \
  results/external/longmemeval-faithful-port-v3-preparation \
  README.md docs/progress.md

git diff --cached --check
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git commit -m 'feat(evaluation): add LongMemEval faithful-port v3 preparation'
git push origin HEAD:research/personal-state-engine-v0
