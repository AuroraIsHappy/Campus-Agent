"""L4 Memory data models (architecture §4.3). Pure stdlib; importable with plain Python.

Layer names are stable strings (interop with callers / future Hermes memory backend).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional

__all__ = [
    "PREFERENCES", "TASK_LOG", "TASK_BOARD", "KNOWLEDGE", "DAILY_LOG",
    "ALL_LAYERS", "MemoryRecord", "Recall", "MemoryError",
]

# --- layers (architecture §4.3) -----------------------------------------------
PREFERENCES = "preferences"      # identity, major, persona — injected into session ctx
TASK_LOG = "task_log"            # long-horizon task EventLog / DecisionLog
TASK_BOARD = "task_board"        # in-progress / todo / done
KNOWLEDGE = "knowledge"          # user-bound urls / lectures / notes index
DAILY_LOG = "daily_log"          # daily secretary log + tomorrow reminder

ALL_LAYERS = (PREFERENCES, TASK_LOG, TASK_BOARD, KNOWLEDGE, DAILY_LOG)


class MemoryError(Exception):
    """Base for memory-layer failures."""


@dataclass
class MemoryRecord:
    """One memory row. ``embedding`` may be None (FTS-only recall still works)."""
    id: str
    layer: str
    key: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: int = 0          # epoch seconds — passed in, never Date.now() here
    embedding: Optional[list[float]] = None
    pinned: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "layer": self.layer, "key": self.key,
                "content": self.content, "metadata": dict(self.metadata),
                "created_at": self.created_at, "embedding": self.embedding,
                "pinned": self.pinned}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MemoryRecord":
        return cls(id=d["id"], layer=d["layer"], key=d.get("key", ""),
                   content=d.get("content", ""),
                   metadata=dict(d.get("metadata") or {}),
                   created_at=int(d.get("created_at") or 0),
                   embedding=d.get("embedding"),
                   pinned=bool(d.get("pinned", False)))


@dataclass
class Recall:
    """A retrieval hit: the matched record + a relevance score in [0, ∞)."""
    record: MemoryRecord
    score: float
