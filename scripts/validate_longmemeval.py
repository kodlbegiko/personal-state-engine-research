#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from personal_state_engine.longmemeval import load_longmemeval


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()
    examples = load_longmemeval(args.dataset)
    question_types = Counter(example.question_type for example in examples)
    summary = {
        "dataset": args.dataset.as_posix(),
        "sha256": sha256(args.dataset),
        "examples": len(examples),
        "question_types": dict(sorted(question_types.items())),
        "abstention_questions": sum(example.is_abstention for example in examples),
        "sessions": sum(len(example.sessions) for example in examples),
        "turns": sum(
            len(session.turns)
            for example in examples
            for session in example.sessions
        ),
        "evidence_turns": sum(
            1
            for example in examples
            for session in example.sessions
            for turn in session.turns
            if turn.has_answer
        ),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
