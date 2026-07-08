"""Reminders — aggregate due events + anniversaries and push them (Phase 1.5).

``check_due`` is the pure core: given today's calendar events and the full
anniversary list, it returns the Reminders that should fire (calendar events
happening today, plus the dual-trigger anniversaries for today + tomorrow).

``send_due`` pushes each reminder via an injected ``push_fn`` (default binds to
``campus.mobile.cli.push``) and records per-day idempotency in the memory layer,
so the same reminder never fires twice in one day even if the scheduler ticks
multiple times.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Callable, Iterable, Optional

from campus.life.types import (
    CalendarEvent, Anniversary, Reminder, EVENT, ANNIVERSARY, BIRTHDAY,
)
from campus.memory.types import PREFERENCES

__all__ = ["check_due", "send_due", "build_message", "PushFn"]

# push_fn signature mirrors campus.mobile.cli.push(channel, target, message) -> PushReceipt
PushFn = Callable[..., object]


def _epoch(d: date) -> int:
    """Local-midnight epoch for a date (used as Reminder.due_at)."""
    return int(datetime(d.year, d.month, d.day).timestamp())


def _today_str(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def build_message(reminder: Reminder) -> str:
    """Human-readable push text for a reminder."""
    if reminder.kind == BIRTHDAY:
        return f"🎂 今天是 {reminder.message}！记得送上祝福～"
    if reminder.kind == ANNIVERSARY:
        return f"纪念日提醒：{reminder.message}"
    # calendar event
    return f"📅 今日提醒：{reminder.message}"


def check_due(today_events: Iterable[CalendarEvent],
              annivs: Iterable[Anniversary], today: date,
              *, heads_up: bool = True) -> list[Reminder]:
    """Return all reminders due on ``today``.

    Calendar events for today become EVENT reminders (one per event). For
    anniversaries, when ``heads_up`` is True we include BOTH the day-of
    occurrences (days_ahead=0) and the next-day heads-up (days_ahead=1) so the
    user gets a warning the day before. De-dup is by (kind, event_id).
    """
    # local import to avoid a cycle (anniversaries imports memory types only)
    from campus.life.anniversaries import due_anniversaries

    out: list[Reminder] = []
    day_ts = _epoch(today)

    # calendar events happening today
    for ev in today_events:
        out.append(Reminder(event_id=ev.id, due_at=day_ts,
                            message=f"{ev.title}" + (f"（{ev.location}）" if ev.location else ""),
                            kind=EVENT))

    # anniversaries: day-of
    for a in due_anniversaries(annivs, today, days_ahead=0):
        label = "生日" if a.kind == BIRTHDAY else "纪念日"
        out.append(Reminder(event_id=a.id, due_at=day_ts,
                            message=f"{a.name}的{label}", kind=a.kind))

    # anniversaries: heads-up (tomorrow)
    if heads_up:
        tomorrow = today + timedelta(days=1)
        for a in due_anniversaries(annivs, tomorrow, days_ahead=0):
            label = "生日" if a.kind == BIRTHDAY else "纪念日"
            out.append(Reminder(event_id=a.id, due_at=_epoch(tomorrow),
                                message=f"明天是{a.name}的{label}，提前提醒～",
                                kind=a.kind))
    return out


def _already_sent(memory, key: str) -> bool:
    """Has this dedup key been recorded today? (stored in PREFERENCES layer)."""
    if memory is None:
        return False
    rec = memory.get(PREFERENCES, key)
    return rec is not None


def _mark_sent(memory, key: str, now: int = 0) -> None:
    if memory is None:
        return
    memory.remember(PREFERENCES, key, "1", created_at=now)


def send_due(reminders: Iterable[Reminder], *, channel: str, target: Optional[str],
             push_fn: Optional[PushFn] = None, memory=None,
             today: Optional[date] = None, now: int = 0) -> list:
    """Push each reminder; skip ones already sent today (idempotent).

    ``push_fn`` defaults to ``campus.mobile.cli.push`` (lazy import so this
    module stays importable without campus.mobile installed). Returns the list
    of PushReceipt-like objects (one per actually-sent reminder; skipped ones
    are not in the list).
    """
    if push_fn is None:
        from campus.mobile.cli import push as push_fn  # real default
    if today is None:
        today = date.today()
    day = _today_str(today)

    receipts = []
    for r in reminders:
        key = r.dedup_key(day)
        if _already_sent(memory, key):
            continue
        receipt = push_fn(channel, r.target or target, build_message(r))
        # a push is "sent" if it didn't raise; record idempotency regardless so
        # a transient push failure doesn't spam the user on every tick.
        _mark_sent(memory, key, now)
        receipts.append(receipt)
    return receipts
