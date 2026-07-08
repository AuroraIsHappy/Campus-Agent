"""Full e2e for campus.life (Phase 6 L-E2E): build events + birthday -> run_daily
-> assert push called + DAILY_LOG written. All stubs; no network / no real push."""
import os
import sys
import json
import tempfile
from datetime import date

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from campus.memory.in_memory import InMemoryStore
from campus.memory.types import DAILY_LOG
from campus.life import (
    run_daily, CalendarEvent, Anniversary, BIRTHDAY, calendar_store as cs,
    anniversaries as ann, secretary_log as slog,
)


def _receipt(ok=True):
    class R:
        pass
    r = R()
    r.ok = ok
    r.channel = "feishu"
    r.target = "oc_x"
    r.message_id = "m1"
    r.error = ""
    return r


def _tmp_cal():
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(p)
    return p


def test_run_daily_end_to_end_sends_and_logs():
    m = InMemoryStore()
    cal = _tmp_cal()

    # seed: a class today (recurring weekly) + a birthday today
    cs.add_event(CalendarEvent(id="", title="高数课", start="2026-07-09T08:00",
                               end="2026-07-09T09:40", location="教三301",
                               rrule="WEEKLY"), path=cal)
    ann.add_anniversary(m, Anniversary(id="", name="小明", date="07-09", kind=BIRTHDAY))

    sent = []

    def fake_push(channel, target, message):
        sent.append(message)
        return _receipt()

    today = date(2026, 7, 9)
    result = run_daily(memory=m, today=today, now=1000, channel="feishu",
                       target="oc_x", push_fn=fake_push, calendar_path=cal)

    # reminders sent: the class event + the birthday (today-of)
    assert result.reminders_sent >= 1
    assert any("高数课" in s for s in sent)
    assert any("小明" in s for s in sent)

    # secretary log persisted to DAILY_LOG, readable cross-session style
    log = slog.get_log(m, "2026-07-09")
    assert log is not None
    assert "高数课" in json.dumps(log.entries, ensure_ascii=False)
    assert "小明" in json.dumps(log.entries, ensure_ascii=False)


def test_run_daily_idempotent_second_tick_no_resend():
    m = InMemoryStore()
    cal = _tmp_cal()
    cs.add_event(CalendarEvent(id="", title="高数课", start="2026-07-09T08:00"), path=cal)

    sent = []

    def fake_push(channel, target, message):
        sent.append(message)
        return _receipt()

    today = date(2026, 7, 9)
    run_daily(memory=m, today=today, channel="feishu", target="oc_x",
              push_fn=fake_push, calendar_path=cal)
    n1 = len(sent)
    # second tick same day: idempotent
    run_daily(memory=m, today=today, channel="feishu", target="oc_x",
              push_fn=fake_push, calendar_path=cal)
    assert len(sent) == n1  # nothing re-sent


def test_run_daily_write_log_false_preview():
    m = InMemoryStore()
    cal = _tmp_cal()
    cs.add_event(CalendarEvent(id="", title="高数课", start="2026-07-09T08:00"), path=cal)

    result = run_daily(memory=m, today=date(2026, 7, 9), channel="feishu",
                       target="oc_x", push_fn=lambda *a, **k: _receipt(),
                       calendar_path=cal, write_log=False)
    assert result.log is not None and result.log_id is None
    # not persisted
    assert slog.get_log(m, "2026-07-09") is None


def test_run_daily_no_push_fn_uses_default_cli():
    """When push_fn is None, run_daily should lazily import campus.mobile.cli.push.
    We can't easily assert a real push, but we CAN assert it doesn't crash at
    import time and that the log still gets written (push failures are swallowed
    by the cli.push wrapper which never raises)."""
    m = InMemoryStore()
    cal = _tmp_cal()
    # No events/annivs -> no reminders -> push_fn never called -> safe
    result = run_daily(memory=m, today=date(2026, 7, 11), channel="feishu",
                       target=None, push_fn=None, calendar_path=cal)
    assert result.reminders_sent == 0
    assert slog.get_log(m, "2026-07-11") is not None
