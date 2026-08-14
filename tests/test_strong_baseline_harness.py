from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from personal_state_engine.strong_baseline import AMemUpstreamAdapter

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_memory_baseline_comparison.py"
spec = importlib.util.spec_from_file_location("strong_metrics", SCRIPT)
strong_metrics = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(strong_metrics)


@dataclass
class FakeNote:
    id: str
    content: str
    timestamp: str | None = None
    context: str = "General"
    keywords: list[str] | None = None
    tags: list[str] | None = None
    links: list[str] | None = None


class FakeRetriever:
    def __init__(self) -> None:
        self.corpus = []
        self.embeddings = object()


class FakeUpstream:
    def __init__(self) -> None:
        self.memories = {}
        self.retriever = FakeRetriever()

    def add_note(self, content, time=None, **kwargs):
        mid = f"m{len(self.memories)+1}"
        note = FakeNote(mid, content, time, kwargs.get("context", "General"), kwargs.get("keywords", []), kwargs.get("tags", []), kwargs.get("links", []))
        self.memories[mid] = note
        self.retriever.corpus.append(content)
        return mid

    def find_related_memories(self, query, k=5):
        indices = list(range(min(k, len(self.memories))))
        return "", indices

    def consolidate_memories(self):
        return None


class StrongBaselineTests(unittest.TestCase):
    def test_adapter_is_mechanical_and_deterministic(self):
        upstream = FakeUpstream()
        adapter = AMemUpstreamAdapter(upstream)
        ids = adapter.write_memories([
            {"content": "first", "timestamp": "2026-01-01T00:00:00Z"},
            {"content": "second", "timestamp": "2026-01-02T00:00:00Z"},
        ])
        self.assertEqual(ids, ["m1", "m2"])
        self.assertEqual([row.memory_id for row in adapter.retrieve("query", k=2)], ["m1", "m2"])
        self.assertEqual(adapter.export_state()["source_commit"], AMemUpstreamAdapter.source_commit)
        adapter.reset()
        self.assertEqual(adapter.export_state()["memories"], [])

    def test_metric_reconstruction(self):
        row = strong_metrics.metrics_for_case({"a", "b"}, ["x", "a", "b"])
        self.assertAlmostEqual(row["recall_at_1"], 0.0)
        self.assertAlmostEqual(row["recall_at_3"], 1.0)
        self.assertAlmostEqual(row["mrr"], 0.5)
        self.assertGreater(row["ndcg_at_5"], 0.0)

    def test_abstention_metric(self):
        row = strong_metrics.metrics_for_case(set(), [])
        self.assertEqual(row["recall_at_1"], 1.0)
        self.assertEqual(row["ndcg_at_5"], 1.0)


if __name__ == "__main__":
    unittest.main()
