"""Life engine — the daily orchestrator (Phase 1.5).

``run_daily`` is the single entry point the scheduler (API background loop or
Hermes cron) calls once a day (or every tick). It:

1. Reads today's calendar events + all anniversaries from the stores.
2. Computes due reminders (events + dual-trigger anniversaries).
3. Pushes them via ``push_fn`` (idempotent — skips already-sent-today).
4. Builds & persists the daily secretary log to the DAILY_LOG layer.

All dependencies (memory, push_fn, calendar path, channel/target) are injected,
so tests run with zero network / zero real push / zero wall clock. ``now`` and
``today`` are explicit parameters (same convention as ``ebbinghaus``).
"""
from __future__ import annotations
from datetime import date, datetime
from typing import Callable, Optional

from campus.life import anniversaries as ann
from campus.life import calendar_store as cs
from campus.life import reminders as rem
from campus.life import secretary_log as slog
from campus.life.types import SecretaryLog

__all__ = ["run_daily", "DailyResult"]


class DailyResult:
    """Outcome of one run_daily tick (plain container — no dataclass dependency)."""

    def __init__(self, *, reminders_sent: int, log: Optional[SecretaryLog],
                 log_id: Optional[str] = None):
        self.reminders_sent = reminders_sent
        self.log = log
        self.log_id = log_id


def _day_bounds(d: date) -> tuple[str, str]:
    """[start_of_day, start_of_next_day) ISO window for ``d``."""
    start = d.strftime("%Y-%m-%dT00:00")
    nxt = date(d.year, d.month, d.day)
    from datetime import timedelta as _td
    end = (nxt + _td(days=1)).strftime("%Y-%m-%dT00:00")
    return start, end


def run_daily(*, memory, today: Optional[date] = None, now: int = 0,
              channel: str = "feishu", target: Optional[str] = None,
              push_fn: Optional[Callable] = None,
              calendar_path: Optional[str] = None,
              tasks: Optional[list] = None,
              write_log: bool = True) -> DailyResult:
    """Run one daily tick. Returns a DailyResult (reminders pushed + log built).

    Parameters
    ----------
    memory : MemoryPort
        Anniversary storage + idempotency + DAILY_LOG sink (inject InMemoryStore
        for tests, JsonFileStore for production).
    today : date, optional
        Defaults to ``date.today()`` — pass explicitly for deterministic tests.
    now : int
        Epoch seconds for record timestamps.
    channel, target : str
        Push destination.
    push_fn : callable, optional
        ``f(channel, target, message) -> receipt``. Defaults to campus.mobile.cli.push.
    calendar_path : str, optional
        Override calendar.json location (tests use a temp file).
    tasks : list, optional
        Extra task items (anything with ``.title``) folded into the secretary log.
    write_log : bool
        If False, build the log but don't persist it (useful for previews).
    """
    if today is None:
        today = date.today()
    if tasks is None:
        tasks = []

    # 1. gather today's events + all anniversaries
    start, end = _day_bounds(today)
    events = cs.list_events(start, end, path=calendar_path)
    annivs = ann.list_anniversaries(memory)

    # 2. compute due reminders (events today + anniv dual-trigger)
    reminders = rem.check_due(events, annivs, today)

    # 3. push (idempotent)
    receipts = rem.send_due(reminders, channel=channel, target=target,
                            push_fn=push_fn, memory=memory, today=today, now=now)

    # 4. build + persist secretary log
    log = slog.build_log(today, events=events, tasks=tasks, reminders=reminders, now=now)
    log_id = slog.write_log(memory, log) if write_log else None

    return DailyResult(reminders_sent=len(receipts), log=log, log_id=log_id)
