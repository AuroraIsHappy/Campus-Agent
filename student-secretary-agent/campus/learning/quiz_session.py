"""Quiz session store (Phase 9 — GOAL.md 定时 quiz 推送 + 问答闭环).

When the scheduler pushes a daily quiz to Feishu/QQ, it stores the pushed
questions (with their ``review_node_id``s) here as a "pending session". When the
user replies with answers in chat, ``handle_mobile_command`` checks for an
active session and routes the reply to grading instead of the generic agent.

Stored in the memory PREFERENCES layer (same idempotency home as reminders),
keyed by ``pending_quiz:<channel>:<target>`` (one active quiz per chat).
"""
from __future__ import annotations

import json
import time
from typing import Any, Optional

__all__ = ["QuizSessionStore"]


class QuizSessionStore:
    """Persist pushed-quiz sessions so inbound answers can be graded.

    A session is ``{questions:[{id, question, answer, review_node_id}], topic,
    pushed_at, channel, target}``. Only one active session per (channel,target).
    """

    def __init__(self, memory=None) -> None:
        if memory is None:
            try:
                from campus.memory.json_store import JsonFileStore
                memory = JsonFileStore()
            except Exception:
                memory = None
        self._memory = memory

    def _key(self, channel: str, target: str) -> str:
        return f"pending_quiz:{channel or 'feishu'}:{target or 'default'}"

    def start(self, *, questions: list[dict[str, Any]], topic: str,
              channel: str = "feishu", target: str = "",
              now: Optional[int] = None) -> bool:
        """Record a pushed quiz session. Returns True on success."""
        if self._memory is None or not questions:
            return False
        now = int(now if now is not None else time.time())
        try:
            from campus.memory.types import PREFERENCES
            self._memory.remember(
                PREFERENCES, self._key(channel, target),
                json.dumps({"questions": questions, "topic": topic,
                            "pushed_at": now, "channel": channel,
                            "target": target}, ensure_ascii=False),
                metadata={"kind": "pending_quiz", "topic": topic})
            return True
        except Exception:
            return False

    def active_for(self, channel: str, target: str) -> Optional[dict[str, Any]]:
        """Return the active pending quiz session, or None."""
        if self._memory is None:
            return None
        try:
            from campus.memory.types import PREFERENCES
            rec = self._memory.get(PREFERENCES, self._key(channel, target))
            if not rec:
                return None
            data = json.loads(rec.content) if isinstance(rec.content, str) else rec.content
            if isinstance(data, dict) and data.get("questions"):
                return data
        except Exception:
            pass
        return None

    def close(self, channel: str, target: str) -> bool:
        """Clear the active session (after grading)."""
        if self._memory is None:
            return False
        try:
            from campus.memory.types import PREFERENCES
            rec = self._memory.get(PREFERENCES, self._key(channel, target))
            if rec and rec.id:
                self._memory.forget(rec.id)
                return True
        except Exception:
            pass
        return False
