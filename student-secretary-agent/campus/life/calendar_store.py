"""Local calendar store — ~/.campus/calendar.json (Phase 1.5).

Pure stdlib JSON store for CalendarEvent. Supports add / update / delete / list,
plus a simplified RRULE expansion (DAILY / WEEKLY) that materializes a recurring
event into concrete instances inside a query window. The store is a thin file
wrapper; all time reasoning goes through ``datetime`` with a caller-supplied
``now`` (the store itself holds no clock).

Design note: calendar events live in their own file (not the memory layer)
because they are structured, frequently mutated (add/delete), and queried by
time window — a poor fit for the FTS/vector memory layer, which is optimised for
free-text recall. Birthdays/anniversaries (rarely change, keyed by id) DO use
the memory layer (see anniversaries.py).
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timedelta
from typing import Optional

from campus.life.types import CalendarEvent

__all__ = [
    "DEFAULT_CALENDAR_PATH", "load", "save", "add_event", "update_event",
    "delete_event", "list_events", "expand_instances", "next_id",
]

DEFAULT_CALENDAR_PATH = os.path.expanduser("~/.campus/calendar.json")
_FMT = "%Y-%m-%dT%H:%M"   # ISO naive local time (calendar event start/end)


def _read(path: str) -> list[CalendarEvent]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    out = []
    for d in data.get("events", []):
        try:
            out.append(CalendarEvent.from_dict(d))
        except (KeyError, TypeError):
            continue
    return out


def load(path: Optional[str] = None) -> list[CalendarEvent]:
    """Load all events from the calendar file."""
    return _read(path or DEFAULT_CALENDAR_PATH)


def save(events: list[CalendarEvent], path: Optional[str] = None) -> None:
    """Persist the full event list (atomic-ish: write whole file)."""
    p = path or DEFAULT_CALENDAR_PATH
    parent = os.path.dirname(p)
    if parent:
        os.makedirs(parent, exist_ok=True)
    data = {"events": [e.to_dict() for e in events]}
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def next_id(events: list[CalendarEvent]) -> str:
    """Next monotonic id: ``evt-<n>`` based on the max existing n."""
    n = 0
    for e in events:
        tail = str(e.id).rsplit("-", 1)[-1]
        try:
            v = int(tail)
            if v > n:
                n = v
        except ValueError:
            continue
    return f"evt-{n + 1}"


def add_event(event: CalendarEvent, *, path: Optional[str] = None,
              now: int = 0) -> CalendarEvent:
    """Append ``event`` (assigning an id if blank) and persist. Returns the stored event."""
    events = load(path)
    if not event.id:
        event.id = next_id(events)
    if not event.created_at:
        event.created_at = now
    events.append(event)
    save(events, path)
    return event


def update_event(event_id: str, patch: dict, *,
                 path: Optional[str] = None) -> Optional[CalendarEvent]:
    """Merge ``patch`` into the event with ``event_id``. Returns updated or None."""
    events = load(path)
    for e in events:
        if e.id == event_id:
            for k, v in patch.items():
                if v is not None and hasattr(e, k):
                    setattr(e, k, v)
            save(events, path)
            return e
    return None


def delete_event(event_id: str, *, path: Optional[str] = None) -> bool:
    """Remove event ``event_id``. Returns True if something was removed."""
    events = load(path)
    before = len(events)
    events = [e for e in events if e.id != event_id]
    if len(events) != before:
        save(events, path)
        return True
    return False


def _parse(dt: str) -> Optional[datetime]:
    try:
        return datetime.strptime(dt, _FMT)
    except (ValueError, TypeError):
        return None


def expand_instances(event: CalendarEvent, window_start: datetime,
                     window_end: datetime) -> list[tuple[datetime, CalendarEvent]]:
    """Materialize a (possibly recurring) event into concrete instances in a window.

    Returns ``[(instance_start, event), ...]`` sorted by start time. For a
    one-off event (rrule None/""/unsupported), yields at most the single start
    if it falls in [window_start, window_end). For DAILY/WEEKLY, steps from the
    event start by the recurrence interval until past window_end.

    Unsupported rrule values (anything besides DAILY/WEEKLY/None/"") are
    treated as a one-off on ``start`` (stored verbatim, not expanded).
    """
    start = _parse(event.start)
    if start is None:
        return []
    rrule = (event.rrule or "").upper() or None
    step: Optional[timedelta] = None
    if rrule == "DAILY":
        step = timedelta(days=1)
    elif rrule == "WEEKLY":
        step = timedelta(weeks=1)
    # else: one-off (None / "" / unsupported -> single instance)

    out: list[tuple[datetime, CalendarEvent]] = []
    if step is None:
        if window_start <= start < window_end:
            out.append((start, event))
        return out

    # recurring: walk forward from start; skip instances before the window
    cur = start
    # if start is way before the window, jump forward in whole steps (no dateutil)
    if cur < window_start:
        delta = window_start - cur
        jumps = int(delta // step)
        cur = cur + jumps * step
    while cur < window_end:
        if cur >= window_start:
            out.append((cur, event))
        cur = cur + step
    return out


def list_events(window_start: Optional[str] = None, window_end: Optional[str] = None,
                *, path: Optional[str] = None) -> list[CalendarEvent]:
    """List events, optionally filtered to an ISO time window [start, end).

    ``window_start`` / ``window_end`` are "YYYY-MM-DDTHH:MM" (same format as
    event.start). Recurring events are expanded into concrete instances within
    the window (each instance is returned as a separate CalendarEvent with the
    instance's start time). If no window is given, returns stored events as-is.
    """
    events = load(path)
    if window_start is None and window_end is None:
        return list(events)
    ws = _parse(window_start) if window_start else datetime.min
    we = _parse(window_end) if window_end else datetime.max
    if ws is None:
        ws = datetime.min
    if we is None:
        we = datetime.max
    out: list[CalendarEvent] = []
    for e in events:
        for inst_start, _src in expand_instances(e, ws, we):
            inst = CalendarEvent(
                id=e.id, title=e.title, start=inst_start.strftime(_FMT),
                end=_shift_end(e.end, e.start, inst_start), rrule=e.rrule,
                location=e.location, note=e.note, created_at=e.created_at)
            out.append(inst)
    out.sort(key=lambda ev: ev.start)
    return out


def _shift_end(end: Optional[str], base_start: str, inst_start: datetime) -> Optional[str]:
    """Recompute an instance's end relative to its shifted start (preserve duration)."""
    if not end:
        return None
    base = _parse(base_start)
    e_end = _parse(end)
    if base is None or e_end is None:
        return end
    duration = e_end - base
    return (inst_start + duration).strftime(_FMT)
