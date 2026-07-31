#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

from personal_state_engine.external_trials import (
    ExternalTrialConfig,
    canonical_sha256,
    execute_trial,
    sha256_file,
    write_immutable_trial,
)
from personal_state_engine.longmemeval import load_longmemeval
from personal_state_engine.model_adapters import ReplayAdapter, RunManifest, SubprocessJSONAdapter


def _code_commit() -> str:
    value = os.environ.get("GITHUB_SHA")
    if value:
        return value
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "UNAVAILABLE"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one immutable LongMemEval external-model trial."
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--baseline", choices=("EXT-B0", "EXT-B5"), required=True)
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("results/raw/external"),
    )
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--split", default="development")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--retrieval-k", type=int, default=5)
    adapter = parser.add_mutually_exclusive_group(required=True)
    adapter.add_argument("--replay", type=Path)
    adapter.add_argument("--adapter-command", nargs=argparse.REMAINDER)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    examples = load_longmemeval(args.dataset)
    selected = [example for example in examples if example.question_id == args.case_id]
    if len(selected) != 1:
        print(
            json.dumps(
                {
                    "error": "case-selection-failed",
                    "case_id": args.case_id,
                    "matches": len(selected),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    manifest = RunManifest.from_json(args.manifest)
    if args.replay is not None:
        model_adapter = ReplayAdapter.from_jsonl(args.replay)
    else:
        command = args.adapter_command or []
        if command and command[0] == "--":
            command = command[1:]
        model_adapter = SubprocessJSONAdapter(command)

    dataset_sha256 = sha256_file(args.dataset)
    split_manifest_sha256 = canonical_sha256(
        {
            "dataset_sha256": dataset_sha256,
            "split": args.split,
            "case_ids": [example.question_id for example in examples],
        }
    )
    run_id = args.run_id or f"external-{uuid.uuid4()}"
    config = ExternalTrialConfig(
        run_id=run_id,
        dataset_name="LongMemEval-S",
        dataset_version=args.dataset_version,
        dataset_sha256=dataset_sha256,
        split_name=args.split,
        split_manifest_sha256=split_manifest_sha256,
        baseline_id=args.baseline,
        baseline_version="external-baseline-v1",
        retrieval_item_limit=args.retrieval_k,
        code_commit=_code_commit(),
    )
    record = execute_trial(selected[0], manifest, config, model_adapter)
    output = write_immutable_trial(record, args.output_directory)
    print(
        json.dumps(
            {
                "trial_id": record.trial_id,
                "request_id": record.request_id,
                "status": record.status,
                "output": str(output),
                "dataset_sha256": record.dataset_sha256,
                "configuration_sha256": record.configuration_sha256,
            },
            sort_keys=True,
        )
    )
    return 0 if record.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
