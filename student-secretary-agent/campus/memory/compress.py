"""Compression / forgetting (architecture §4.3, 'Claude dreams' pattern).

Pure transforms over record lists: sediment a batch of old records into one summary
record on the preferences/knowledge layer, and prune records older than a retention
window (pinned records are always kept). The summarize step is an **injected** function
(default: metadata['summary']-or-truncate — never an LLM call) so tests stay hermetic
and nothing is fabricated. Real summarization plugs in without changing callers.
"""
from __future__ import annotations
from typing import Callable, Iterable, Optional

from campus.memory.types import MemoryRecord, PREFERENCES

__all__ = ["compress", "prune_by_window", "default_summarizer", "Summarizer"]

Summarizer = Callable[[list[MemoryRecord]], str]


def default_summarizer(records: list[MemoryRecord]) -> str:
    """No-LLM summary: prefer each record's metadata['summary'], else first line of content."""
    parts = []
    for r in records:
        meta = getattr(r, "metadata", None) or {}
        s = meta.get("summary")
        if not s:
            content = (getattr(r, "content", "") or "").strip()
            s = content.split("\n", 1)[0][:160] if content else ""
        if s:
            parts.append(f"- {s}")
    return "\n".join(parts)


def compress(old_records: Iterable[MemoryRecord],
             summarizer: Optional[Summarizer] = None, *,
             sink_layer: str = PREFERENCES, key: str = "sediment",
             created_at: int = 0) -> Optional[MemoryRecord]:
    """Sediment non-pinned old records into one MemoryRecord on ``sink_layer``.

    Returns None when there is nothing to summarize (no non-pinned records, or the
    summarizer produced empty output). Never fabricates content — only rephrases what
    the records already carry (via the summarizer).
    """
    summarizer = summarizer or default_summarizer
    recs = [r for r in old_records if not getattr(r, "pinned", False)]
    if not recs:
        return None
    summary = summarizer(recs)
    if not summary or not summary.strip():
        return None
    return MemoryRecord(
        id=f"{sink_layer}-sediment-{created_at}",
        layer=sink_layer, key=key, content=summary,
        metadata={"sedimented_from": len(recs)}, created_at=created_at,
    )


def prune_by_window(records: Iterable[MemoryRecord], now_ts: int,
                    retention_seconds: int) -> list[MemoryRecord]:
    """Drop records older than the retention window; always keep pinned records."""
    cutoff = now_ts - retention_seconds
    kept = []
    for r in records:
        if getattr(r, "pinned", False):
            kept.append(r)
            continue
        if (getattr(r, "created_at", 0) or 0) >= cutoff:
            kept.append(r)
    return kept
