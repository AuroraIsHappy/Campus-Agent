"""Campus life module (Phase 1.5) — calendar, anniversaries, daily secretary log.

Public surface re-exported here so callers do ``from campus.life import ...``
without reaching into submodules. See each submodule's docstring for detail.
"""
from campus.life.types import (
    CalendarEvent, Anniversary, Reminder, SecretaryLog,
    BIRTHDAY, ANNIVERSARY, EVENT,
)
from campus.life import calendar_store, anniversaries, reminders, secretary_log
from campus.life.engine import run_daily, DailyResult

__all__ = [
    # types
    "CalendarEvent", "Anniversary", "Reminder", "SecretaryLog",
    "BIRTHDAY", "ANNIVERSARY", "EVENT",
    # submodules
    "calendar_store", "anniversaries", "reminders", "secretary_log",
    # engine
    "run_daily", "DailyResult",
]
