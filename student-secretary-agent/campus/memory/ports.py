"""L4 Memory ports (architecture §C4②): Campus depends only on ``MemoryPort`` /
``EmbedderPort``, never on a concrete backend. Backends (``InMemoryStore``,
``JsonFileStore``) live in this package. Pure Protocol; no third-party imports.

The recall() return type is ``list[Recall]`` (duck-typed here as ``list`` to keep the
Protocol free of an import cycle — concrete backends return ``Recall`` objects).
"""
from __future__ import annotations
from typing import Any, Iterable, Optional, Protocol, runtime_checkable

__all__ = ["MemoryPort", "EmbedderPort", "RetrieverPort", "RECALL_MODES"]

RECALL_MODES = ("hybrid", "fts", "vector")


@runtime_checkable
class EmbedderPort(Protocol):
    """text -> vector. Default deterministic impl (HashEmbedder) keeps tests hermetic;
    real embedding models plug in here without changing callers."""
    dim: int

    def embed(self, text: str) -> list[float]: ...


@runtime_checkable
class MemoryPort(Protocol):
    """The thin memory surface Campus depends on. ``layer`` ∈ ALL_LAYERS."""

    def remember(self, layer: str, key: str, content: str,
                 metadata: Optional[dict[str, Any]] = None,
                 pinned: bool = False, created_at: int = 0) -> str: ...

    def recall(self, query: str, *, layers: Iterable[str] = (),
               k: int = 5, mode: str = "hybrid") -> list: ...

    def get(self, layer: str, key: str) -> Optional[Any]: ...

    def list_layer(self, layer: str) -> list: ...

    def forget(self, record_id: str) -> bool: ...

    def all(self) -> list: ...


@runtime_checkable
class RetrieverPort(Protocol):
    """Combine FTS + vector. The default hybrid retriever lives in ``in_memory``."""

    def fts(self, query: str, records: list, k: int) -> list: ...

    def vector(self, query: str, records: list, k: int) -> list: ...
