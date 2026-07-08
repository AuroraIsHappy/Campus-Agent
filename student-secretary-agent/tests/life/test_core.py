"""Unit tests for campus.life calendar_store (Phase 6 L-CAL1/CAL2). Pure stdlib, no clock."""
import os
import sys
import tempfile

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from campus.life.types import CalendarEvent
from campus.life import calendar_store as cs


def _tmp():
    """A fresh temp calendar path for one test (isolated file per call)."""
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(p)  # start clean (no file)
    return p


# ---------------- CRUD (L-CAL1) ----------------

def test_add_assigns_id_and_persists():
    p = _tmp()
    e = cs.add_event(
        CalendarEvent(id="", title="高数课", start="2026-07-09T08:00",
                      end="2026-07-09T09:40", location="教三301"),
        path=p, now=1000)
    assert e.id == "evt-1" and e.created_at == 1000
    loaded = cs.load(p)
    assert len(loaded) == 1 and loaded[0].title == "高数课"


def test_next_id_monotonic_skips_non_numeric():
    p = _tmp()
    cs.add_event(CalendarEvent(id="evt-2", title="a", start="2026-07-01T08:00"), path=p)
    cs.add_event(CalendarEvent(id="weird-xx", title="b", start="2026-07-02T08:00"), path=p)
    assert cs.next_id(cs.load(p)) == "evt-3"


def test_list_no_window_returns_as_is():
    p = _tmp()
    cs.add_event(CalendarEvent(id="", title="x", start="2026-07-09T08:00"), path=p)
    assert len(cs.list_events(path=p)) == 1


def test_update_merges_patch_returns_updated():
    p = _tmp()
    e = cs.add_event(CalendarEvent(id="", title="会", start="2026-07-09T10:00"), path=p)
    upd = cs.update_event(e.id, {"location": "线上", "title": "周会"}, path=p)
    assert upd is not None and upd.location == "线上" and upd.title == "周会"
    got = cs.load(p)[0]
    assert got.location == "线上" and got.start == "2026-07-09T10:00"  # untouched fields kept


def test_update_missing_returns_none():
    p = _tmp()
    assert cs.update_event("nope", {"title": "x"}, path=p) is None


def test_delete_removes_and_returns_bool():
    p = _tmp()
    e = cs.add_event(CalendarEvent(id="", title="x", start="2026-07-09T08:00"), path=p)
    assert cs.delete_event(e.id, path=p) is True
    assert cs.delete_event(e.id, path=p) is False  # already gone
    assert cs.load(p) == []


def test_load_missing_file_returns_empty():
    assert cs.load(_tmp()) == []


# ---------------- RRULE expansion (L-CAL2) ----------------

def test_expand_one_off_inside_window():
    from datetime import datetime
    e = CalendarEvent(id="e1", title="once", start="2026-07-03T08:00")
    insts = cs.expand_instances(e, datetime(2026, 7, 1), datetime(2026, 7, 10))
    assert len(insts) == 1


def test_expand_one_off_outside_window_yields_none():
    from datetime import datetime
    e = CalendarEvent(id="e1", title="once", start="2026-07-15T08:00")
    insts = cs.expand_instances(e, datetime(2026, 7, 1), datetime(2026, 7, 10))
    assert insts == []


def test_expand_daily_7_instances_in_7day_window():
    from datetime import datetime
    e = CalendarEvent(id="e1", title="daily", start="2026-07-01T08:00", rrule="DAILY")
    insts = cs.expand_instances(e, datetime(2026, 7, 1), datetime(2026, 7, 8))
    assert len(insts) == 7  # Jul 1..7


def test_expand_weekly_7_instances_in_7week_window():
    from datetime import datetime
    e = CalendarEvent(id="e1", title="wk", start="2026-07-01T08:00", rrule="WEEKLY")
    insts = cs.expand_instances(e, datetime(2026, 7, 1), datetime(2026, 8, 19))  # 7 weeks
    assert len(insts) == 7


def test_expand_jumps_forward_when_start_before_window():
    from datetime import datetime
    # event started 2026-01-01, daily; query a 3-day window in July
    e = CalendarEvent(id="e1", title="daily", start="2026-01-01T08:00", rrule="DAILY")
    insts = cs.expand_instances(e, datetime(2026, 7, 1), datetime(2026, 7, 4))
    assert len(insts) == 3  # Jul 1,2,3
    assert insts[0][0].day == 1 and insts[2][0].day == 3


def test_expand_unsupported_rrule_treated_as_oneoff():
    from datetime import datetime
    e = CalendarEvent(id="e1", title="m", start="2026-07-03T08:00", rrule="MONTHLY")
    insts = cs.expand_instances(e, datetime(2026, 7, 1), datetime(2026, 7, 10))
    assert len(insts) == 1  # not expanded, just the start if in-window


def test_list_window_expands_and_sorts_and_shifts_end():
    p = _tmp()
    cs.add_event(CalendarEvent(id="", title="课", start="2026-07-01T08:00",
                               end="2026-07-01T09:40", rrule="WEEKLY"), path=p)
    cs.add_event(CalendarEvent(id="", title="单次", start="2026-07-05T20:00"), path=p)
    out = cs.list_events("2026-07-01T00:00", "2026-07-15T00:00", path=p)
    # weekly Jul1,8 + one-off Jul5 = 3, sorted by start
    assert [o.start for o in out] == ["2026-07-01T08:00", "2026-07-05T20:00", "2026-07-08T08:00"]
    # end shifted: weekly instance on Jul8 keeps the 1h40 duration -> 09:40
    wk = [o for o in out if o.start.startswith("2026-07-08")][0]
    assert wk.end == "2026-07-08T09:40"


def test_list_window_bad_iso_falls_back_gracefully():
    p = _tmp()
    cs.add_event(CalendarEvent(id="", title="x", start="2026-07-09T08:00"), path=p)
    out = cs.list_events("not-a-date", None, path=p)  # bad start -> treat as min
    assert any(o.title == "x" for o in out)


def test_add_with_explicit_id_keeps_it():
    p = _tmp()
    e = cs.add_event(CalendarEvent(id="my-id", title="x", start="2026-07-09T08:00"), path=p)
    assert e.id == "my-id"


# ---------------- Anniversaries (L-ANN1/ANN2) ----------------

from campus.memory.in_memory import InMemoryStore
from campus.memory.types import PREFERENCES
from campus.life.types import Anniversary, BIRTHDAY, ANNIVERSARY
from campus.life import anniversaries as ann
from datetime import date


def _mem():
    return InMemoryStore()


def test_anniv_add_assigns_id_and_persists():
    m = _mem()
    a = ann.add_anniversary(m, Anniversary(id="", name="小明", date="07-09",
                                           kind=BIRTHDAY), now=1000)
    assert a.id == "anniv-1"
    listed = ann.list_anniversaries(m)
    assert len(listed) == 1 and listed[0].name == "小明" and listed[0].kind == BIRTHDAY


def test_anniv_add_with_explicit_id_kept():
    m = _mem()
    a = ann.add_anniversary(m, Anniversary(id="my-a", name="结婚", date="02-14",
                                           kind=ANNIVERSARY))
    assert a.id == "my-a"
    assert ann.list_anniversaries(m)[0].kind == ANNIVERSARY


def test_anniv_next_id_monotonic():
    m = _mem()
    ann.add_anniversary(m, Anniversary(id="anniv-2", name="a", date="01-01"), now=1)
    ann.add_anniversary(m, Anniversary(id="weird", name="b", date="01-02"), now=1)
    assert ann.next_id(ann.list_anniversaries(m)) == "anniv-3"


def test_anniv_list_filters_non_anniv_prefs():
    m = _mem()
    m.remember(PREFERENCES, "something_else", "not an anniv")
    ann.add_anniversary(m, Anniversary(id="anniv-1", name="x", date="03-01"))
    listed = ann.list_anniversaries(m)
    assert len(listed) == 1  # the unrelated pref is excluded


def test_anniv_delete():
    m = _mem()
    a = ann.add_anniversary(m, Anniversary(id="anniv-1", name="x", date="03-01"))
    assert ann.delete_anniversary(m, a.id) is True
    assert ann.delete_anniversary(m, a.id) is False  # already gone
    assert ann.list_anniversaries(m) == []


def test_next_occurrence_today():
    # birthday today
    assert ann.next_occurrence("07-09", date(2026, 7, 9)) == date(2026, 7, 9)


def test_next_occurrence_passed_rolls_next_year():
    # July 9 birthday, today is July 10 -> next is 2027-07-09
    assert ann.next_occurrence("07-09", date(2026, 7, 10)) == date(2027, 7, 9)


def test_next_occurrence_future_same_year():
    assert ann.next_occurrence("12-25", date(2026, 7, 9)) == date(2026, 12, 25)


def test_next_occurrence_feb29_nonleap():
    # Feb-29 in 2026 (non-leap) -> Feb-28
    assert ann.next_occurrence("02-29", date(2026, 1, 1)) == date(2026, 2, 28)


def test_next_occurrence_bad_date_none():
    assert ann.next_occurrence("13-40", date(2026, 7, 9)) is None
    assert ann.next_occurrence("garbage", date(2026, 7, 9)) is None


def test_due_today_trigger():
    annivs = [Anniversary(id="a1", name="小明", date="07-09", kind=BIRTHDAY)]
    due = ann.due_anniversaries(annivs, date(2026, 7, 9), days_ahead=0)
    assert [a.id for a in due] == ["a1"]


def test_due_tomorrow_trigger():
    annivs = [Anniversary(id="a1", name="小明", date="07-09", kind=BIRTHDAY)]
    due = ann.due_anniversaries(annivs, date(2026, 7, 8), days_ahead=1)  # today=8, due=9
    assert [a.id for a in due] == ["a1"]


def test_due_not_in_range():
    annivs = [Anniversary(id="a1", name="小明", date="07-09", kind=BIRTHDAY)]
    assert ann.due_anniversaries(annivs, date(2026, 7, 1), days_ahead=0) == []
    assert ann.due_anniversaries(annivs, date(2026, 7, 9), days_ahead=1) == []


def test_due_skips_malformed():
    annivs = [
        Anniversary(id="a1", name="好", date="07-09"),
        Anniversary(id="a2", name="坏", date="bad"),
    ]
    due = ann.due_anniversaries(annivs, date(2026, 7, 9), days_ahead=0)
    assert [a.id for a in due] == ["a1"]  # malformed skipped, no raise


def test_due_dual_trigger_dedup():
    # When engine calls days_ahead=1 then 0, the same anniv appears on both days
    # (heads-up + day-of). This test documents that the two calls return the
    # anniv on the right day; dedup across calls is the engine's job.
    annivs = [Anniversary(id="a1", name="小明", date="07-09")]
    assert ann.due_anniversaries(annivs, date(2026, 7, 8), days_ahead=1)  # heads-up
    assert ann.due_anniversaries(annivs, date(2026, 7, 9), days_ahead=0)  # day-of
    # neither on the wrong day:
    assert not ann.due_anniversaries(annivs, date(2026, 7, 8), days_ahead=0)
    assert not ann.due_anniversaries(annivs, date(2026, 7, 9), days_ahead=1)


# ---------------- Reminders (L-REM1/REM2) ----------------

from campus.life.types import Reminder, EVENT, ANNIVERSARY, BIRTHDAY
from campus.life import reminders as rem
from types import SimpleNamespace


def _receipt(ok=True):
    return SimpleNamespace(ok=ok, channel="feishu", target="oc_x",
                           message_id="m1", error="")


def test_check_due_collects_events_and_annivs():
    today = date(2026, 7, 9)
    events = [CalendarEvent(id="e1", title="高数课", start="2026-07-09T08:00",
                            location="教三301")]
    annivs = [Anniversary(id="a1", name="小明", date="07-09", kind=BIRTHDAY)]
    due = rem.check_due(events, annivs, today)
    kinds = sorted(r.kind for r in due)
    assert EVENT in kinds and BIRTHDAY in kinds
    # the event reminder carries the location
    ev_r = [r for r in due if r.kind == EVENT][0]
    assert "高数课" in ev_r.message and "教三301" in ev_r.message


def test_check_due_heads_up_for_tomorrow_birthday():
    # today is the 8th; a birthday on the 9th should produce a heads-up reminder
    today = date(2026, 7, 8)
    annivs = [Anniversary(id="a1", name="小明", date="07-09", kind=BIRTHDAY)]
    due = rem.check_due([], annivs, today, heads_up=True)
    msgs = [r.message for r in due]
    assert any("明天" in m and "小明" in m for m in msgs)


def test_check_due_no_heads_up_when_disabled():
    today = date(2026, 7, 8)
    annivs = [Anniversary(id="a1", name="小明", date="07-09", kind=BIRTHDAY)]
    due = rem.check_due([], annivs, today, heads_up=False)
    assert due == []  # nothing today-of, and heads-up suppressed


def test_build_message_variants():
    assert "🎂" in rem.build_message(Reminder("x", 0, "小明", BIRTHDAY))
    assert "纪念日" in rem.build_message(Reminder("x", 0, "结婚记", ANNIVERSARY))
    assert "📅" in rem.build_message(Reminder("x", 0, "高数课", EVENT))


def test_send_due_calls_push_fn_per_reminder():
    sent = []
    def fake(channel, target, message):
        sent.append((channel, target, message))
        return _receipt()
    rs = [Reminder("e1", 0, "高数课", EVENT), Reminder("a1", 0, "小明", BIRTHDAY)]
    receipts = rem.send_due(rs, channel="feishu", target="oc_x", push_fn=fake,
                            memory=None, today=date(2026, 7, 9))
    assert len(receipts) == 2 == len(sent)
    assert all(r.ok for r in receipts)


def test_send_due_idempotent_skips_already_sent():
    m = _mem()
    sent = []
    def fake(channel, target, message):
        sent.append(message)
        return _receipt()
    rs = [Reminder("e1", 0, "高数课", EVENT)]
    # first tick: sends
    r1 = rem.send_due(rs, channel="feishu", target="oc_x", push_fn=fake,
                      memory=m, today=date(2026, 7, 9), now=1)
    assert len(r1) == 1 and len(sent) == 1
    # second tick same day: skipped (idempotent)
    r2 = rem.send_due(rs, channel="feishu", target="oc_x", push_fn=fake,
                      memory=m, today=date(2026, 7, 9), now=2)
    assert r2 == [] and len(sent) == 1  # not sent again


def test_send_due_new_day_resends():
    m = _mem()
    sent = []
    def fake(channel, target, message):
        sent.append(message)
        return _receipt()
    rs = [Reminder("e1", 0, "高数课", EVENT)]
    rem.send_due(rs, channel="feishu", target="oc_x", push_fn=fake,
                 memory=m, today=date(2026, 7, 9), now=1)
    # next day: dedup key changes -> sends again
    r2 = rem.send_due(rs, channel="feishu", target="oc_x", push_fn=fake,
                      memory=m, today=date(2026, 7, 10), now=2)
    assert len(r2) == 1 and len(sent) == 2


# ---------------- Secretary log (L-LOG1) ----------------

from campus.life import secretary_log as slog
from campus.life.types import SecretaryLog
from campus.memory.types import DAILY_LOG
from types import SimpleNamespace


def test_build_log_summarizes_events_and_tasks():
    today = date(2026, 7, 9)
    events = [CalendarEvent(id="e1", title="高数课", start="2026-07-09T08:00",
                            location="教三301")]
    tasks = [SimpleNamespace(title="交实验报告")]
    log = slog.build_log(today, events=events, tasks=tasks, now=1000)
    assert log.date == "2026-07-09"
    assert "1 个日程" in log.summary and "1 个任务" in log.summary
    assert any("高数课" in e and "教三301" in e for e in log.entries)
    assert any("交实验报告" in e for e in log.entries)
    assert log.created_at == 1000


def test_build_log_includes_fired_anniv_reminders():
    today = date(2026, 7, 9)
    rem = [Reminder("a1", 0, "今天是小明的生日", BIRTHDAY),
           Reminder("e1", 0, "高数课", EVENT)]
    log = slog.build_log(today, events=[], reminders=rem)
    # anniversary reminder becomes an entry; event reminder does NOT (events are entries themselves)
    assert any("小明" in e for e in log.entries)


def test_build_log_tomorrow_from_heads_up():
    today = date(2026, 7, 8)
    rem = [Reminder("a1", 0, "明天是小明的生日，提前提醒～", BIRTHDAY)]
    log = slog.build_log(today, events=[], reminders=rem)
    assert any("小明" in t for t in log.tomorrow)


def test_write_and_get_log_roundtrip():
    m = _mem()
    log = SecretaryLog(date="2026-07-09", summary="test", entries=["a"], tomorrow=["b"])
    rid = slog.write_log(m, log)
    assert rid
    got = slog.get_log(m, "2026-07-09")
    assert got is not None and got.summary == "test" and got.entries == ["a"]


def test_get_log_missing_returns_none():
    m = _mem()
    assert slog.get_log(m, "2026-07-09") is None


def test_recent_logs_newest_first():
    m = _mem()
    for d in ["2026-07-01", "2026-07-09", "2026-07-05"]:
        slog.write_log(m, SecretaryLog(date=d, summary=d))
    recent = slog.recent_logs(m, 7)
    assert [lg.date for lg in recent] == ["2026-07-09", "2026-07-05", "2026-07-01"]


def test_recent_logs_excludes_non_daily_keys():
    m = _mem()
    m.remember(DAILY_LOG, "something_else", "{}")  # unrelated DAILY_LOG record
    slog.write_log(m, SecretaryLog(date="2026-07-09", summary="x"))
    assert len(slog.recent_logs(m, 7)) == 1


def test_log_to_markdown_sections():
    log = SecretaryLog(date="2026-07-09", summary="今天有 1 个日程",
                       entries=["08:00 高数课（教三301）"], tomorrow=["明天是小明的生日"])
    md = log.to_markdown()
    assert "# 秘书日志 · 2026-07-09" in md
    assert "## 今日" in md and "高数课" in md
    assert "## 明日提醒" in md and "小明" in md


# ---------------- Engine (L-ENG1) ----------------

from campus.life import engine
from types import SimpleNamespace


def _receipt2():
    return SimpleNamespace(ok=True, channel="feishu", target="oc_x",
                           message_id="m1", error="")


def _tmp_cal():
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(p)
    return p


def test_engine_run_daily_folds_tasks_into_log():
    m = _mem()
    cal = _tmp_cal()
    cs.add_event(CalendarEvent(id="", title="高数课", start="2026-07-09T08:00"), path=cal)
    tasks = [SimpleNamespace(title="交实验报告")]
    result = engine.run_daily(memory=m, today=date(2026, 7, 9), channel="feishu",
                              target="oc_x", push_fn=lambda *a, **k: _receipt2(),
                              calendar_path=cal, tasks=tasks)
    assert result.log is not None
    assert any("交实验报告" in e for e in result.log.entries)
    assert result.log_id is not None


def test_engine_run_daily_recurring_event_today():
    m = _mem()
    cal = _tmp_cal()
    # weekly event whose base start is weeks ago, recurring into today
    cs.add_event(CalendarEvent(id="", title="周会", start="2026-06-28T10:00",
                               rrule="WEEKLY"), path=cal)
    # 2026-07-09 is a Wednesday; let's pick a today that hits a weekly instance.
    # Jun 28 is a Sunday -> Sundays: Jul 5, 12. Use Jul 5.
    sent = []
    result = engine.run_daily(memory=m, today=date(2026, 7, 5), channel="feishu",
                              target="oc_x",
                              push_fn=lambda *a, **k: (sent.append(a[2]) or _receipt2()),
                              calendar_path=cal)
    assert result.reminders_sent >= 1
    assert any("周会" in s for s in sent)


def test_engine_run_daily_default_today_no_crash():
    # today=None should resolve to date.today() without error
    m = _mem()
    cal = _tmp_cal()
    result = engine.run_daily(memory=m, channel="feishu", target=None,
                              push_fn=lambda *a, **k: _receipt2(), calendar_path=cal)
    assert result.log is not None
