from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class UpstreamAMem(Protocol):
    memories: dict[str, Any]

    def add_note(self, content: str, time: str | None = None, **kwargs: Any) -> str: ...
    def find_related_memories(self, query: str, k: int = 5) -> tuple[str, list[int]]: ...
    def consolidate_memories(self) -> None: ...


@dataclass(frozen=True, slots=True)
class RetrievedMemory:
    memory_id: str
    rank: int
    content: str
    timestamp: str | None


class AMemUpstreamAdapter:
    """Mechanical adapter over the exact-pinned upstream A-MEM API.

    This class intentionally does not reimplement A-MEM's semantic algorithm.
    It maps the project's common memory interface onto an upstream
    RobustAgenticMemorySystem/AgenticMemorySystem instance. Tests may inject a
    fake upstream object to validate interface mechanics without claiming
    algorithmic reproduction.
    """

    baseline_id = "A-MEM"
    source_commit = "0c8039f28fdcc08189a23c07a3437d9d2482f9c2"

    def __init__(self, upstream: UpstreamAMem) -> None:
        self._upstream = upstream

    def reset(self) -> None:
        memories = getattr(self._upstream, "memories", None)
        if memories is None or not hasattr(memories, "clear"):
            raise RuntimeError("upstream A-MEM object does not expose mutable memories")
        memories.clear()
        retriever = getattr(self._upstream, "retriever", None)
        if retriever is not None:
            corpus = getattr(retriever, "corpus", None)
            if hasattr(corpus, "clear"):
                corpus.clear()
            if hasattr(retriever, "embeddings"):
                retriever.embeddings = None

    def write_memory(self, event: dict[str, Any] | str) -> str:
        if isinstance(event, str):
            return self._upstream.add_note(event)
        content = str(event["content"])
        timestamp = event.get("timestamp")
        metadata = {
            key: event[key]
            for key in ("keywords", "links", "importance_score", "context", "category", "tags")
            if key in event
        }
        return self._upstream.add_note(content, time=timestamp, **metadata)

    def write_memories(self, events: list[dict[str, Any] | str]) -> list[str]:
        return [self.write_memory(event) for event in events]

    def retrieve(self, query: str, k: int = 5) -> list[RetrievedMemory]:
        if k < 1:
            raise ValueError("k must be >= 1")
        _, indices = self._upstream.find_related_memories(query, k=k)
        ordered = list(self._upstream.memories.values())
        result: list[RetrievedMemory] = []
        for rank, index in enumerate(indices, start=1):
            if index < 0 or index >= len(ordered):
                raise RuntimeError(f"upstream returned out-of-range memory index: {index}")
            note = ordered[index]
            result.append(
                RetrievedMemory(
                    memory_id=str(note.id),
                    rank=rank,
                    content=str(note.content),
                    timestamp=getattr(note, "timestamp", None),
                )
            )
        return result

    def update_memory(self, event: dict[str, Any] | str) -> str:
        # Upstream A-MEM implements update/evolution as part of add_note().
        return self.write_memory(event)

    def build_context(self, query: str, budget: int, k: int = 5) -> str:
        if budget < 0:
            raise ValueError("budget must be >= 0")
        pieces: list[str] = []
        used = 0
        for memory in self.retrieve(query, k=k):
            line = f"[{memory.memory_id}] {memory.content}"
            tokens = line.split()
            remaining = budget - used
            if remaining <= 0:
                break
            if len(tokens) > remaining:
                line = " ".join(tokens[:remaining])
            pieces.append(line)
            used += min(len(tokens), remaining)
        return "\n".join(pieces)

    def export_state(self) -> dict[str, Any]:
        rows = []
        for note in self._upstream.memories.values():
            rows.append(
                {
                    "id": str(note.id),
                    "content": str(note.content),
                    "timestamp": getattr(note, "timestamp", None),
                    "context": getattr(note, "context", None),
                    "keywords": list(getattr(note, "keywords", []) or []),
                    "tags": list(getattr(note, "tags", []) or []),
                    "links": list(getattr(note, "links", []) or []),
                }
            )
        return {"baseline_id": self.baseline_id, "source_commit": self.source_commit, "memories": rows}

    def resource_stats(self) -> dict[str, Any]:
        return {
            "memory_count": len(self._upstream.memories),
            "algorithm_runtime_measured": False,
            "note": "Mechanical adapter only; upstream model/embedding resource use must be measured in the pinned runtime.",
        }
