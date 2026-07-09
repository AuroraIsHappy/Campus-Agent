"""Conversation history store (Phase 9 — GOAL.md 聊天优先).

Persists multi-turn chat threads keyed by ``conversation_id`` so the web chat
(and mobile inbound) can maintain a real back-and-forth — unlike the prior
``mobile_commands.json`` which was a flat single-turn audit log.

Storage mirrors the JSON-file convention of ``campus/runtime/stores.py``
(``state/conversations.json``). Pure I/O, no clock — ``now`` is injected.
"""
from __future__ import annotations
import json
import os
import time
import uuid
from typing import Any, Optional

from campus.runtime.paths import state_dir

__all__ = ["ConversationStore", "new_conversation_id"]


def new_conversation_id() -> str:
    return f"conv_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


class ConversationStore:
    """Append-only multi-turn conversation store.

    On-disk shape (``state/conversations.json``)::

        {"<conv_id>": {
            "id": "<conv_id>",
            "title": "<first user message, truncated>",
            "created_at": <ts>,
            "updated_at": <ts>,
            "messages": [
                {"role": "user"|"assistant", "content": "...",
                 "run_id": "...", "ts": <ts>, "persona": "..."},
                ...
            ]
        }, ...}
    """

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path or os.path.join(state_dir(), "conversations.json")

    # ---- read ----
    def _all(self) -> dict[str, dict[str, Any]]:
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save(self, data: dict[str, dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get(self, conversation_id: str) -> Optional[dict[str, Any]]:
        if not conversation_id:
            return None
        return self._all().get(conversation_id)

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        records = list(self._all().values())
        records.sort(key=lambda r: r.get("updated_at", 0), reverse=True)
        # return summaries (no full message bodies) to keep payloads small
        out = []
        for r in records[:limit]:
            out.append({
                "id": r.get("id", ""),
                "title": r.get("title", ""),
                "created_at": r.get("created_at", 0),
                "updated_at": r.get("updated_at", 0),
                "message_count": len(r.get("messages", [])),
            })
        return out

    def history(self, conversation_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Return the last ``limit`` messages of a conversation (oldest→newest)."""
        conv = self.get(conversation_id)
        if not conv:
            return []
        msgs = conv.get("messages", [])
        return msgs[-limit:] if limit else msgs

    # ---- write ----
    def append(self, *, conversation_id: Optional[str], role: str, content: str,
               run_id: str = "", persona: str = "", now: Optional[int] = None
               ) -> dict[str, Any]:
        """Append a message to a conversation, creating it if needed.

        Returns the (possibly new) ``conversation_id``.
        """
        now = int(now if now is not None else time.time())
        data = self._all()
        if not conversation_id or conversation_id not in data:
            conversation_id = conversation_id or new_conversation_id()
            data[conversation_id] = {
                "id": conversation_id,
                "title": content[:60] if role == "user" else "新对话",
                "created_at": now,
                "updated_at": now,
                "messages": [],
            }
        conv = data[conversation_id]
        conv["messages"].append({
            "role": role,
            "content": content,
            "run_id": run_id,
            "persona": persona,
            "ts": now,
        })
        conv["updated_at"] = now
        if role == "user" and not conv.get("title"):
            conv["title"] = content[:60]
        self._save(data)
        return {"conversation_id": conversation_id}

    def delete(self, conversation_id: str) -> bool:
        data = self._all()
        if conversation_id in data:
            del data[conversation_id]
            self._save(data)
            return True
        return False
