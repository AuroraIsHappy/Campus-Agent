"""User-preferences injection + maintenance (Phase 9.1).

PREFERENCES is the user's long-term profile (identity, major, persona, onboarding
answers, auto-learned habits). Unlike TASK_LOG / KNOWLEDGE which need semantic
retrieval, PREFERENCES is small + high-value → **inject every turn, full-layer**,
no scoring/truncation-by-relevance.

This module provides:
- ``load_preferences_block(memory)``: full-layer read → formatted prompt section.
- ``maintain_preferences(memory)``: scheduled cleanup (dedup, prune stale, cap size).
"""
from __future__ import annotations

import time
from typing import Any, Optional

from campus.memory.types import PREFERENCES, MemoryRecord

__all__ = ["load_preferences_block", "maintain_preferences", "MAX_PREF_CHARS"]

MAX_PREF_CHARS = 2000  # cap the injected block; PREFERENCES should stay small


def load_preferences_block(memory=None) -> str:
    """Read ALL PREFERENCES records and format them into a prompt section.

    Returns a ``=== 用户偏好 ===`` block ready to paste into an LLM prompt.
    If no PREFERENCES exist, returns "" (caller omits the section).
    Capped at MAX_PREF_CHARS; truncation is annotated.
    """
    if memory is None:
        try:
            from campus.memory.json_store import JsonFileStore
            memory = JsonFileStore()
        except Exception:
            return ""
    try:
        records = memory.list_layer(PREFERENCES)
    except Exception:
        return ""
    if not records:
        return ""

    # sort: pinned first, then by created_at descending (newest first)
    records.sort(key=lambda r: (not r.pinned, -(r.created_at or 0)))

    lines = ["=== 用户偏好（每轮自动注入） ==="]
    total = 0
    for rec in records:
        # format: key: content (skip sediment/summary blobs that are too long)
        content = (rec.content or "").strip()
        if not content:
            continue
        # truncate individual entries that are absurdly long
        if len(content) > 300:
            content = content[:300] + "…"
        line = f"- {rec.key}: {content}"
        if total + len(line) > MAX_PREF_CHARS:
            lines.append(f"  …（偏好过多，已截断；共 {len(records)} 条）")
            break
        lines.append(line)
        total += len(line)

    if len(lines) <= 1:  # only the header, no content
        return ""
    return "\n".join(lines)


def maintain_preferences(memory=None, *, now: Optional[int] = None,
                         max_age_days: int = 180,
                         max_records: int = 50) -> dict[str, Any]:
    """Scheduled cleanup of the PREFERENCES layer.

    - Removes duplicate keys (keeps the newest).
    - Prunes non-pinned records older than ``max_age_days``.
    - Caps total records at ``max_records`` (pinned always kept).

    Returns a summary dict {kept, removed, deduped}.
    Returns {error: ...} if memory is unavailable.
    """
    if memory is None:
        try:
            from campus.memory.json_store import JsonFileStore
            memory = JsonFileStore()
        except Exception as e:
            return {"error": str(e)}
    now = int(now if now is not None else time.time())
    max_age_s = max_age_days * 86400

    try:
        records = memory.list_layer(PREFERENCES)
    except Exception as e:
        return {"error": str(e)}

    removed = 0
    deduped = 0

    # 1. dedup by key: keep newest per key
    by_key: dict[str, MemoryRecord] = {}
    for r in records:
        existing = by_key.get(r.key)
        if existing is None or (r.created_at or 0) > (existing.created_at or 0):
            if existing is not None:
                # forget the older duplicate
                try:
                    memory.forget(existing.id)
                    deduped += 1
                except Exception:
                    pass
            by_key[r.key] = r
        else:
            try:
                memory.forget(r.id)
                deduped += 1
            except Exception:
                pass

    # 2. prune stale non-pinned
    kept = list(by_key.values())
    for r in kept:
        if not r.pinned and (now - (r.created_at or 0)) > max_age_s:
            try:
                memory.forget(r.id)
                removed += 1
            except Exception:
                pass

    # 3. cap: if still too many, drop oldest non-pinned
    remaining = [r for r in kept if r.pinned or (now - (r.created_at or 0)) <= max_age_s]
    remaining.sort(key=lambda r: (r.pinned, r.created_at or 0), reverse=True)
    if len(remaining) > max_records:
        for r in remaining[max_records:]:
            if not r.pinned:
                try:
                    memory.forget(r.id)
                    removed += 1
                except Exception:
                    pass

    final_count = max(0, len(remaining) - removed)

    return {"kept": final_count, "removed": removed, "deduped": deduped}
