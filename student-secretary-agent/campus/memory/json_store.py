"""JsonFileStore — MemoryPort impl backed by a JSON file (default ~/.campus/memory.json).

Proves cross-session recall (S-MEMORY): a fresh instance that loads the same file
remembers everything written by a previous instance. Embeddings are persisted too, so
recall works after reload without re-embedding. Delegates recall to ``InMemoryStore``
after loading; persists on every mutating call.
"""
from __future__ import annotations
import json
import os
from typing import Any, Iterable, Optional

from campus.memory.embedding import HashEmbedder
from campus.memory.in_memory import InMemoryStore
from campus.memory.ports import EmbedderPort
from campus.memory.types import MemoryRecord, Recall

__all__ = ["JsonFileStore", "DEFAULT_MEMORY_PATH"]

DEFAULT_MEMORY_PATH = os.path.expanduser("~/.campus/memory.json")


def _default_memory_path() -> str:
    try:
        from campus.runtime.paths import campus_home
        return os.path.join(campus_home(), "memory.json")
    except Exception:
        return DEFAULT_MEMORY_PATH


class JsonFileStore:
    """File-backed memory store. Composes an ``InMemoryStore`` for query logic."""

    def __init__(self, path: Optional[str] = None,
                 embedder: Optional[EmbedderPort] = None) -> None:
        self.path = path or _default_memory_path()
        self._store = InMemoryStore(embedder=embedder or HashEmbedder())
        self._load()

    # --- persistence ----------------------------------------------------
    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return
        for d in data.get("records", []):
            try:
                rec = MemoryRecord.from_dict(d)
            except (KeyError, TypeError):
                continue
            self._store._records[rec.id] = rec
            try:
                n = int(str(rec.id).rsplit("-", 1)[-1])
                if n > self._store._seq:
                    self._store._seq = n
            except ValueError:
                pass

    def _save(self) -> None:
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        data = {"records": [r.to_dict() for r in self._store._records.values()]}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # --- MemoryPort surface (delegate; persist on writes) ---------------
    def remember(self, layer: str, key: str, content: str,
                 metadata: Optional[dict[str, Any]] = None,
                 pinned: bool = False, created_at: int = 0) -> str:
        rid = self._store.remember(layer, key, content, metadata, pinned, created_at)
        self._save()
        return rid

    def recall(self, query: str, *, layers: Iterable[str] = (),
               k: int = 5, mode: str = "hybrid") -> list[Recall]:
        return self._store.recall(query, layers=layers, k=k, mode=mode)

    def get(self, layer: str, key: str) -> Optional[MemoryRecord]:
        return self._store.get(layer, key)

    def list_layer(self, layer: str) -> list[MemoryRecord]:
        return self._store.list_layer(layer)

    def forget(self, record_id: str) -> bool:
        ok = self._store.forget(record_id)
        if ok:
            self._save()
        return ok

    def all(self) -> list[MemoryRecord]:
        return self._store.all()
