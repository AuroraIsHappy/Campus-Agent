"""Daily secretary log — the end-of-day summary (Phase 1.5).

``build_log`` is the pure core: from today's calendar events, the user's task
list, and today's due reminders, it composes a ``SecretaryLog`` (a summary line
+ bullet entries + tomorrow's heads-up list). ``write_log`` persists it to the
``DAILY_LOG`` memory layer keyed by date; ``get_log`` / ``recent_logs`` read it
back. Cross-session recall works because JsonFileStore persists.

This is the layer the GOAL calls "每日秘书日志": every night the engine builds
one and (optionally) pushes it to the user's mobile.
"""
from __future__ import annotations
import json
from datetime import date, timedelta
from typing import Any, Iterable, Optional

from campus.life.types import CalendarEvent, SecretaryLog, Reminder, EVENT
from campus.memory.types import DAILY_LOG

__all__ = [
    "build_log", "write_log", "get_log", "recent_logs", "log_key",
]


def log_key(day: str) -> str:
    """Memory key for a day's log: ``daily:<YYYY-MM-DD>``."""
    return f"daily:{day}"


def _fmt_event(ev: CalendarEvent) -> str:
    when = ev.start[11:] if len(ev.start) >= 16 else ""  # HH:MM
    loc = f"（{ev.location}）" if ev.location else ""
    return f"{when} {ev.title}{loc}".strip()


def build_log(today: date, *, events: Iterable[CalendarEvent],
              tasks: Iterable[Any] = (), reminders: Iterable[Reminder] = (),
              now: int = 0) -> SecretaryLog:
    """Compose the daily log for ``today``.

    - ``events``: today's calendar events (already filtered to today by caller).
    - ``tasks``: anything with a ``.title`` / ``["title"]`` (Odyssey tasks, todos).
    - ``reminders``: the reminders that fired today (anniversaries etc.).
    Produces a one-line summary + entries (events + done-ish tasks) + tomorrow
    (reminder heads-ups already phrased for tomorrow).
    """
    ev_list = list(events)
    task_list = list(tasks)
    rem_list = list(reminders)

    entries: list[str] = [_fmt_event(e) for e in ev_list]
    for t in task_list:
        title = getattr(t, "title", None) or (t.get("title") if isinstance(t, dict) else "")
        if title:
            entries.append(f"任务：{title}")
    # anniversary reminders that fired today read as "今天是小明的生日"
    for r in rem_list:
        if r.kind != EVENT:
            entries.append(r.message)

    tomorrow_str = (today + timedelta(days=1)).isoformat()
    # tomorrow = tomorrow's events (caller may pass them in `events` if they
    # include tomorrow; otherwise we surface reminder heads-ups already phrased
    # for tomorrow). We keep it simple: any reminder whose message starts with
    # "明天" goes to the tomorrow list.
    tomorrow: list[str] = [r.message for r in rem_list if r.message.startswith("明天")]

    n_events = len(ev_list)
    n_tasks = len(task_list)
    summary = f"今天有 {n_events} 个日程"
    if n_tasks:
        summary += f"、{n_tasks} 个任务"

    return SecretaryLog(date=today.isoformat(), summary=summary,
                        entries=entries, tomorrow=tomorrow, created_at=now)


def write_log(memory, log: SecretaryLog) -> str:
    """Persist ``log`` to the DAILY_LOG layer (keyed by date). Returns the record id."""
    import time as _t
    ts = log.created_at or int(_t.time())
    return memory.remember(DAILY_LOG, log_key(log.date),
                           json.dumps(log.to_dict(), ensure_ascii=False),
                           metadata={"date": log.date}, created_at=ts)


def _to_log(rec: Any) -> Optional[SecretaryLog]:
    if rec is None:
        return None
    content = getattr(rec, "content", None)
    if content:
        try:
            return SecretaryLog.from_dict(json.loads(content))
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    return None


def get_log(memory, day: str) -> Optional[SecretaryLog]:
    """Read one day's log (``day`` = "YYYY-MM-DD"), or None if absent."""
    rec = memory.get(DAILY_LOG, log_key(day))
    return _to_log(rec)


def recent_logs(memory, n: int = 7) -> list[SecretaryLog]:
    """Most recent N logs, newest first (by date string sort)."""
    out: list[SecretaryLog] = []
    for rec in memory.list_layer(DAILY_LOG):
        key = getattr(rec, "key", "")
        if not str(key).startswith("daily:"):
            continue
        log = _to_log(rec)
        if log is not None:
            out.append(log)
    out.sort(key=lambda lg: lg.date, reverse=True)
    return out[:n]
