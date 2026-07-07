"""InMemoryStore — MemoryPort impl with FTS (token overlap) + vector (cosine) hybrid recall.

No persistence (see ``JsonFileStore`` for cross-session). Hermetic: inject any
``EmbedderPort`` (default deterministic ``HashEmbedder``) — no network, no model.
"""
from __future__ import annotations
from typing import Any, Iterable, Optional

from campus.memory.embedding import HashEmbedder, cosine_sim, tokenize
from campus.memory.ports import EmbedderPort
from campus.memory.types import ALL_LAYERS, MemoryRecord, Recall

__all__ = ["InMemoryStore", "fts_score"]


def fts_score(query: str, record: MemoryRecord) -> float:
    """Fraction of query tokens present in the record's key+content+metadata values.

    Returns 0.0 when the query has no tokens (so it never spuriously matches).
    """
    q_tokens = set(tokenize(query))
    if not q_tokens:
        return 0.0
    hay = " ".join([
        record.key or "",
        record.content or "",
        " ".join(str(v) for v in (record.metadata or {}).values()),
    ])
    h_tokens = set(tokenize(hay))
    if not h_tokens:
        return 0.0
    return len(q_tokens & h_tokens) / len(q_tokens)


class InMemoryStore:
    """In-memory multi-layer store with hybrid FTS+vector recall."""

    def __init__(self, embedder: Optional[EmbedderPort] = None) -> None:
        self.embedder = embedder if embedder is not None else HashEmbedder()
        self._records: dict[str, MemoryRecord] = {}
        self._seq = 0

    # --- writes ---------------------------------------------------------
    def remember(self, layer: str, key: str, content: str,
                 metadata: Optional[dict[str, Any]] = None,
                 pinned: bool = False, created_at: int = 0) -> str:
        if layer not in ALL_LAYERS:
            raise ValueError(f"unknown memory layer: {layer!r}")
        self._seq += 1
        rid = f"{layer}-{self._seq}"
        emb = None
        if self.embedder is not None:
            emb = self.embedder.embed(f"{key} {content}")
        rec = MemoryRecord(id=rid, layer=layer, key=key or "", content=content or "",
                           metadata=dict(metadata or {}), created_at=created_at,
                           embedding=emb, pinned=bool(pinned))
        self._records[rid] = rec
        return rid

    def forget(self, record_id: str) -> bool:
        return self._records.pop(record_id, None) is not None

    # --- reads ----------------------------------------------------------
    def get(self, layer: str, key: str) -> Optional[MemoryRecord]:
        for r in self._records.values():
            if r.layer == layer and r.key == key:
                return r
        return None

    def list_layer(self, layer: str) -> list[MemoryRecord]:
        return [r for r in self._records.values() if r.layer == layer]

    def all(self) -> list[MemoryRecord]:
        return list(self._records.values())

    # --- retrieval ------------------------------------------------------
    def recall(self, query: str, *, layers: Iterable[str] = (),
               k: int = 5, mode: str = "hybrid") -> list[Recall]:
        if mode not in ("hybrid", "fts", "vector"):
            raise ValueError(f"unknown recall mode: {mode!r}")
        layer_set = set(layers) if layers else set(ALL_LAYERS)
        pool = [r for r in self._records.values() if r.layer in layer_set]
        if not pool:
            return []
        hits: dict[str, Recall] = {}

        if mode in ("hybrid", "fts"):
            for r in pool:
                s = fts_score(query, r)
                if s > 0:
                    hits[r.id] = Recall(record=r, score=s)

        if mode in ("hybrid", "vector") and self.embedder is not None:
            q_vec = self.embedder.embed(query)
            for r in pool:
                if not r.embedding:
                    continue
                s = cosine_sim(q_vec, r.embedding)
                if s <= 0:
                    continue
                if r.id in hits:
                    hits[r.id] = Recall(record=r, score=hits[r.id].score + s)
                else:
                    hits[r.id] = Recall(record=r, score=s)

        ranked = sorted(hits.values(), key=lambda rc: rc.score, reverse=True)
        return ranked[:k]
