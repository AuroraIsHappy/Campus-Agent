"""Ebbinghaus forgetting-curve review scheduler (architecture §4.3).

Pure functions: no cron, no clock. Callers pass timestamps (epoch seconds). Intervals
follow an SM-2-ish growing schedule. ``advance()`` encodes 'correct -> +1, wrong -> 0'.
The caller persists reps_correct/last_ts and wires the cron; this module only computes.
"""
from __future__ import annotations
from typing import Any, Iterable

__all__ = [
    "INTERVALS_DAYS", "SECONDS_PER_DAY", "interval_days",
    "next_review", "advance", "due_items", "schedule",
]

# SM-2-ish growing intervals (days). After the table, grow by ~1.8x per correct rep.
INTERVALS_DAYS = (1, 3, 7, 16, 35)
SECONDS_PER_DAY = 86_400


def interval_days(reps_correct: int) -> int:
    """Days until the next review given the number of consecutive correct reps."""
    if reps_correct < 0:
        reps_correct = 0
    if reps_correct < len(INTERVALS_DAYS):
        return INTERVALS_DAYS[reps_correct]
    last = INTERVALS_DAYS[-1]
    extra = reps_correct - (len(INTERVALS_DAYS) - 1)
    return int(last * (1.8 ** extra))


def next_review(reps_correct: int, last_ts: int) -> int:
    """Scheduled due timestamp = last review + interval (epoch seconds)."""
    return last_ts + interval_days(reps_correct) * SECONDS_PER_DAY


def advance(reps_correct: int, correct: bool) -> int:
    """Update consecutive-correct count: +1 on correct, reset to 0 on wrong."""
    return reps_correct + 1 if correct else 0


def _get(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def due_items(items: Iterable[Any], now_ts: int) -> list:
    """Items whose scheduled review is due (due_ts <= now_ts).

    Each item exposes ``reps_correct`` and ``last_ts`` (attr or key).
    """
    out = []
    for it in items:
        last = _get(it, "last_ts")
        if last is None:
            continue
        reps = _get(it, "reps_correct") or 0
        if next_review(reps, last) <= now_ts:
            out.append(it)
    return out


def schedule(items: Iterable[Any], now_ts: int = 0) -> list[tuple]:
    """Return [(item, due_ts)] sorted by due_ts (soonest first)."""
    out = []
    for it in items:
        last = _get(it, "last_ts")
        if last is None:
            continue
        reps = _get(it, "reps_correct") or 0
        out.append((it, next_review(reps, last)))
    out.sort(key=lambda t: t[1])
    return out
