"""Anniversaries & birthdays — year-less recurring reminders (Phase 1.5).

Stored in the memory layer's ``PREFERENCES`` stratum, keyed ``anniv:<id>``, so
they persist across sessions (JsonFileStore) and travel with the user profile.
``date`` is "MM-DD" (no year) → recurs every year; the next occurrence is
computed against the current year at query time.

Dual-trigger logic (architecture §4.3): a birthday fires both the day *before*
(a heads-up) and *on the day*. ``due_anniversaries(today, days_ahead)`` is the
pure core; callers (reminders/engine) call it twice (days_ahead=1 then 0) and
dedup by id.
"""
from __future__ import annotations
import json
from datetime import date
from typing import Any, Iterable, Optional

from campus.life.types import Anniversary, BIRTHDAY, ANNIVERSARY
from campus.memory.types import PREFERENCES

__all__ = [
    "ANNIV_PREFIX", "add_anniversary", "list_anniversaries", "delete_anniversary",
    "next_occurrence", "due_anniversaries", "next_id",
]

ANNIV_PREFIX = "anniv:"   # memory key prefix: anniv:<id>


def _key(aid: str) -> str:
    return f"{ANNIV_PREFIX}{aid}"


def _to_anniv(rec: Any) -> Optional[Anniversary]:
    """Coerce a memory record (MemoryRecord or dict) into an Anniversary, or None."""
    if rec is None:
        return None
    if hasattr(rec, "content"):
        d = json.loads(rec.content) if rec.content else {}
        if hasattr(rec, "metadata") and rec.metadata:
            d = {**d, **rec.metadata}
    elif isinstance(rec, dict):
        d = dict(rec)
    else:
        return None
    try:
        return Anniversary.from_dict(d)
    except Exception:
        return None


def next_id(existing: Iterable[Anniversary]) -> str:
    """Next monotonic id ``anniv-<n>`` from existing anniv-* ids."""
    n = 0
    for a in existing:
        tail = str(a.id).rsplit("-", 1)[-1]
        try:
            v = int(tail)
            if v > n:
                n = v
        except ValueError:
            continue
    return f"anniv-{n + 1}"


def add_anniversary(memory, anniv: Anniversary, *, now: int = 0) -> Anniversary:
    """Persist ``anniv`` into the PREFERENCES layer. Assigns an id if blank.

    ``memory`` is a MemoryPort (InMemoryStore / JsonFileStore / injected stub).
    """
    if not anniv.id:
        existing = list_anniversaries(memory)
        anniv.id = next_id(existing)
    memory.remember(PREFERENCES, _key(anniv.id), json.dumps(anniv.to_dict()),
                    metadata=anniv.to_dict(), created_at=now or 0)
    return anniv


def list_anniversaries(memory) -> list[Anniversary]:
    """All anniversaries from the PREFERENCES layer (id-sorted, stable order)."""
    out: list[Anniversary] = []
    for rec in memory.list_layer(PREFERENCES):
        if not str(getattr(rec, "key", "") or "").startswith(ANNIV_PREFIX):
            continue
        a = _to_anniv(rec)
        if a is not None:
            out.append(a)
    out.sort(key=lambda a: a.id)
    return out


def delete_anniversary(memory, anniv_id: str) -> bool:
    """Forget the anniv:<id> record. Returns True if removed."""
    rec = memory.get(PREFERENCES, _key(anniv_id))
    if rec is None:
        return False
    rid = getattr(rec, "id", None)
    if rid is None and isinstance(rec, dict):
        rid = rec.get("id")
    if rid is None:
        return False
    return memory.forget(str(rid))


def _parse_mmdd(s: str) -> Optional[tuple[int, int]]:
    """Parse "MM-DD" -> (month, day). Returns None on bad input."""
    try:
        mm, dd = s.split("-", 1)
        m, d = int(mm), int(dd)
        if 1 <= m <= 12 and 1 <= d <= 31:
            return (m, d)
    except (ValueError, AttributeError):
        pass
    return None


def next_occurrence(anniv_date: str, today: date) -> Optional[date]:
    """Next calendar occurrence of an "MM-DD" anniversary on/after ``today``.

    If this year's occurrence already passed, rolls to next year. Returns None
    if ``anniv_date`` is malformed. Feb-29 gracefully maps to Feb-28 in non-leap
    years (date(...) would otherwise raise).
    """
    md = _parse_mmdd(anniv_date)
    if md is None:
        return None
    m, d = md
    y = today.year
    try:
        occ = date(y, m, d)
    except ValueError:
        occ = date(y, 2, 28)  # Feb-29 in a non-leap year -> Feb-28
    if occ < today:
        try:
            occ = date(y + 1, m, d)
        except ValueError:
            occ = date(y + 1, 2, 28)
    return occ


def due_anniversaries(annivs: Iterable[Anniversary], today: date,
                      days_ahead: int = 0) -> list[Anniversary]:
    """Anniversaries whose next occurrence is exactly ``days_ahead`` days from today.

    ``days_ahead=0`` → due today; ``=1`` → due tomorrow (the heads-up trigger).
    Malformed dates and malformed annivs are skipped (never raise).
    """
    out: list[Anniversary] = []
    for a in annivs:
        occ = next_occurrence(a.date, today)
        if occ is None:
            continue
        if (occ - today).days == days_ahead:
            out.append(a)
    out.sort(key=lambda a: a.id)
    return out
