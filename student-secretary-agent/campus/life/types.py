"""Life-module data models (Phase 1.5 — architecture §4.3 / GOAL "状态持久化").

Pure stdlib dataclasses. ``start`` / ``end`` are ISO-8601 strings (naive local
time, e.g. "2026-07-09T08:00"); ``date`` fields are "YYYY-MM-DD" (logs) or
"MM-DD" (anniversaries — year-less so they recur every year). All clocks are
passed in by the caller; nothing here reads the wall clock.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional

__all__ = [
    "CalendarEvent", "Anniversary", "Reminder", "SecretaryLog",
    "BIRTHDAY", "ANNIVERSARY", "EVENT", "ANNIVERSARY_KINDS", "RRULE_KINDS",
]

# --- enums (stable strings; interop with memory layer / callers) ----------------
EVENT = "event"                                   # Reminder.kind for calendar events
BIRTHDAY = "birthday"                             # Anniversary.kind
ANNIVERSARY = "anniversary"                       # Anniversary.kind
ANNIVERSARY_KINDS = (BIRTHDAY, ANNIVERSARY)
RRULE_KINDS = (None, "", "DAILY", "WEEKLY")        # supported recurrence (simplified)


@dataclass
class CalendarEvent:
    """One entry in the local calendar (~/.campus/calendar.json).

    ``start``/``end`` are ISO-8601 naive local time. ``rrule`` ∈ {None, "DAILY",
    "WEEKLY"} — a simplified recurrence (the calendar_store expands it into
    concrete instances inside a time window). Anything else is stored as-is but
    not expanded (treated as a one-off on ``start``).
    """
    id: str
    title: str
    start: str                 # "2026-07-09T08:00"
    end: Optional[str] = None  # "2026-07-09T09:40"
    rrule: Optional[str] = None
    location: str = ""
    note: str = ""
    created_at: int = 0        # epoch seconds — passed in, never time.time()

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "start": self.start,
                "end": self.end, "rrule": self.rrule, "location": self.location,
                "note": self.note, "created_at": self.created_at}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CalendarEvent":
        return cls(id=str(d.get("id", "")), title=str(d.get("title", "")),
                   start=str(d.get("start", "")), end=d.get("end"),
                   rrule=d.get("rrule"), location=str(d.get("location", "")),
                   note=str(d.get("note", "")), created_at=int(d.get("created_at") or 0))


@dataclass
class Anniversary:
    """A year-less recurring day — birthday or memorial day.

    ``date`` is "MM-DD" (no year) so it recurs every year. The next occurrence
    is computed against the current year at query time (anniversaries module).
    Stored in the ``PREFERENCES`` memory layer with key ``anniv:<id>``.
    """
    id: str
    name: str
    date: str                  # "MM-DD"
    kind: str = BIRTHDAY       # one of ANNIVERSARY_KINDS
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "date": self.date,
                "kind": self.kind, "note": self.note}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Anniversary":
        kind = str(d.get("kind", BIRTHDAY))
        if kind not in ANNIVERSARY_KINDS:
            kind = BIRTHDAY
        return cls(id=str(d.get("id", "")), name=str(d.get("name", "")),
                   date=str(d.get("date", "")), kind=kind,
                   note=str(d.get("note", "")))


@dataclass
class Reminder:
    """A due notification: one calendar event-instance or one anniversary.

    ``due_at`` is epoch seconds (when it should fire). ``kind`` is EVENT or
    ANNIVERSARY. ``event_id`` links back to the source CalendarEvent /
    Anniversary (same id space is disambiguated by ``kind``).
    """
    event_id: str
    due_at: int                # epoch seconds
    message: str
    kind: str = EVENT          # EVENT or ANNIVERSARY
    target: Optional[str] = None

    def dedup_key(self, day: str) -> str:
        """Stable per-day key for send idempotency: ``sent:<YYYY-MM-DD>:<kind>:<id>``."""
        return f"sent:{day}:{self.kind}:{self.event_id}"

    def to_dict(self) -> dict[str, Any]:
        return {"event_id": self.event_id, "due_at": self.due_at,
                "message": self.message, "kind": self.kind, "target": self.target}


@dataclass
class SecretaryLog:
    """The daily secretary report (architecture §4.3 — DAILY_LOG layer).

    Built once a day (by ``secretary_log.build_log``) from today's events,
    tasks, and due reminders, then persisted to the ``DAILY_LOG`` memory layer
    keyed by date. Cross-session recall works because JsonFileStore persists.
    """
    date: str                  # "YYYY-MM-DD"
    summary: str = ""
    entries: list[str] = field(default_factory=list)   # what happened today
    tomorrow: list[str] = field(default_factory=list)  # what's due tomorrow
    created_at: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"date": self.date, "summary": self.summary,
                "entries": list(self.entries), "tomorrow": list(self.tomorrow),
                "created_at": self.created_at}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SecretaryLog":
        return cls(date=str(d.get("date", "")), summary=str(d.get("summary", "")),
                   entries=list(d.get("entries") or []),
                   tomorrow=list(d.get("tomorrow") or []),
                   created_at=int(d.get("created_at") or 0))

    def to_markdown(self) -> str:
        """Human-readable daily log (pushed to the user via mobile)."""
        lines = [f"# 秘书日志 · {self.date}"]
        if self.summary:
            lines.append("")
            lines.append(self.summary)
        if self.entries:
            lines.append("")
            lines.append("## 今日")
            for e in self.entries:
                lines.append(f"- {e}")
        if self.tomorrow:
            lines.append("")
            lines.append("## 明日提醒")
            for t in self.tomorrow:
                lines.append(f"- {t}")
        return "\n".join(lines)
