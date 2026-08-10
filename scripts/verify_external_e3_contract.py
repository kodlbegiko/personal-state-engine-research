#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


EXPECTED_SHA256 = {
    ".gitignore": "178e14d442342be3df8e9b107aecd70b4d94608166b148250036d47d9ef60e56",
    ".github/workflows/ci.yml": "4090319ab416f37166f5457dd8863476c3efbc935fc1ced7b329831266e1c1d7",
    ".github/workflows/external-e3-smoke.yml": "73648ab3fcc7a48cabe5973cc9eb4a96d792a84b5e476e9cc1519da989c0ca6b",
    "experiments/configs/smollm2-135m-e3-smoke.json": "9c17b38cab7cab5d63af33d291f7c73e74770598108c05a3a104e9b8d5c96778",
    "experiments/datasets/longmemeval-s-cleaned.json": "a790f09d4934b5ecb22988354feeb3489f35a076907233794516cf6eb3ef19b0",
    "experiments/models/smollm2-135m-instruct-transformersjs.json": "3d8ea69a641dba26601a5d084bd8cb98b0c53ce534a6778259f4e33758e49ab6",
    "experiments/runtime/package.json": "e401f51133165257f2bb9c3fcb7bf69216def8523a7e6e07e6c6694e308c2db7",
    "experiments/runtime/package-lock.json": "85e48061fa8229d13b82a7cea1b9a9942542886b018e791c4e5f8ccfdbae3f48",
    "scripts/transformersjs_model_server.mjs": "68756552f611ab4a03bec3b77432d113ea15263be52f3a58d878def347a0c996"
}


class ContractError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid JSON contract file: {path}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"contract JSON root must be an object: {path}")
    return value


def verify(root: Path = Path(".")) -> None:
    failures = []
    for relative, expected in EXPECTED_SHA256.items():
        path = root / relative
        if not path.is_file():
            failures.append(f"missing:{relative}")
        else:
            actual = sha256(path)
            if actual != expected:
                failures.append(f"hash:{relative}:{actual}")

    dataset = load_json(root / "experiments/datasets/longmemeval-s-cleaned.json")
    model = load_json(root / "experiments/models/smollm2-135m-instruct-transformersjs.json")
    run = load_json(root / "experiments/configs/smollm2-135m-e3-smoke.json")
    package = load_json(root / "experiments/runtime/package.json")

    exact_revision = str(model.get("model_revision", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", exact_revision):
        failures.append("model_revision:not_exact_commit")
    if run.get("model_version") != exact_revision:
        failures.append("model_revision:run_manifest_mismatch")
    if model.get("tokenizer_revision") != exact_revision:
        failures.append("tokenizer_revision:mismatch")
    source_revision = str(dataset.get("source_revision", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", source_revision):
        failures.append("dataset_revision:not_exact_commit")
    if source_revision not in str(dataset.get("download_url", "")):
        failures.append("dataset_url:not_revision_pinned")
    dependencies = package.get("dependencies", {})
    if not isinstance(dependencies, dict) or dependencies.get("@huggingface/transformers") != "4.2.0":
        failures.append("runtime:not_exact_4.2.0")
    if run.get("temperature") != 0.0 or run.get("seed") != 7:
        failures.append("generation_config:not_fixed")

    if failures:
        raise ContractError(", ".join(failures))


if __name__ == "__main__":
    verify()
    print(
        f"verified external E3 execution contract: "
        f"{len(EXPECTED_SHA256)} anchored files"
    )
