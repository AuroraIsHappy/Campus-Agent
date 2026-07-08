"""Sync a generated study/review plan to calendars (Phase 9 — GOAL.md 日历同步).

Bridges the Demo B ``ReviewPlan`` / Demo C ``Plan`` (currently written only as
``plan.md`` run-dir artifacts) into the local calendar store and/or Feishu
calendar — so the schedule the agent generates actually appears where the user
looks, instead of being stranded in a file.

Idempotent: skips events that already exist with the same title + date.
"""
from __future__ import annotations

import datetime as _dt
import time
from typing import Any, Optional

__all__ = ["sync_plan_to_calendar", "sync_review_plan", "sync_demo_c_plan"]


def _to_dt(date_str: str, slot_time: str = "20:00") -> _dt.datetime:
    """Parse 'YYYY-MM-DD' + 'HH:MM' into a datetime."""
    d = _dt.date.fromisoformat(date_str)
    hh, mm = (int(x) for x in (slot_time or "20:00").split(":")[:2])
    return _dt.datetime.combine(d, _dt.time(hh, mm))


def _event_exists(calendar_store, title: str, date_str: str) -> bool:
    """Check if a calendar event with this title already exists on this date."""
    try:
        start = f"{date_str}T00:00"
        end_dt = _dt.date.fromisoformat(date_str) + _dt.timedelta(days=1)
        end = f"{end_dt.isoformat()}T00:00"
        events = calendar_store.list_events(start, end)
        return any(e.title == title for e in events)
    except Exception:
        return False


def sync_review_plan(plan, *, topic: str = "", slot_time: str = "20:00",
                     local: bool = True, feishu: bool = False,
                     now: Optional[int] = None) -> dict[str, Any]:
    """Sync a Demo B ``ReviewPlan`` to calendars.

    Each ``ReviewDay`` becomes one calendar event titled ``复习：<topics>``.
    """
    days = getattr(plan, "days", [])
    return _sync_days(
        days=[{"date": d.date, "topic": ", ".join(d.topics) or topic,
               "minutes": getattr(d, "est_minutes", 20)} for d in days],
        prefix="复习", topic=topic, slot_time=slot_time,
        local=local, feishu=feishu, now=now)


def sync_demo_c_plan(plan, *, slot_time: str = "20:00",
                     local: bool = True, feishu: bool = False,
                     now: Optional[int] = None) -> dict[str, Any]:
    """Sync a Demo C ``Plan`` to calendars. Each ``DayTask`` becomes one event."""
    days = getattr(plan, "days", [])
    return _sync_days(
        days=[{"date": d.date, "topic": d.topic,
               "minutes": getattr(d, "est_minutes", 20)} for d in days],
        prefix="学习", topic=getattr(plan, "goal", ""), slot_time=slot_time,
        local=local, feishu=feishu, now=now)


def _sync_days(days: list[dict[str, Any]], *, prefix: str, topic: str,
               slot_time: str, local: bool, feishu: bool,
               now: Optional[int] = None) -> dict[str, Any]:
    """Internal: sync a list of {date, topic, minutes} day-dicts to calendars."""
    now = int(now if now is not None else time.time())
    result = {"ok": True, "local_created": 0, "local_skipped": 0,
              "feishu_created": 0, "feishu_errors": [], "total_days": len(days)}

    cs = None
    if local:
        try:
            from campus.life import calendar_store as cs_mod
            from campus.life.types import CalendarEvent
            cs = cs_mod
        except Exception:
            local = False

    feishu_syncer = None
    if feishu:
        try:
            from campus.life.feishu_calendar import FeishuCalendarSyncer
            feishu_syncer = FeishuCalendarSyncer()
            hc = feishu_syncer.health_check()
            if not hc["ok"]:
                result["feishu_errors"].append(hc.get("error", "not configured"))
                feishu_syncer = None
        except Exception as e:
            result["feishu_errors"].append(str(e)[:200])
            feishu_syncer = None

    for d in days:
        date_str = d.get("date", "")
        topic_str = d.get("topic", "") or topic or "学习"
        minutes = int(d.get("minutes", 20) or 20)
        if not date_str:
            continue
        title = f"{prefix}：{topic_str}"[:80]
        try:
            start_dt = _to_dt(date_str, slot_time)
            end_dt = start_dt + _dt.timedelta(minutes=minutes)
        except Exception:
            continue

        # ---- local calendar ----
        if local and cs:
            try:
                if _event_exists(cs, title, date_str):
                    result["local_skipped"] += 1
                else:
                    from campus.life.types import CalendarEvent
                    cs.add_event(CalendarEvent(
                        id="", title=title,
                        start=start_dt.strftime("%Y-%m-%dT%H:%M"),
                        end=end_dt.strftime("%Y-%m-%dT%H:%M"),
                        note=f"自动同步自学习计划 ({topic})"), now=now)
                    result["local_created"] += 1
            except Exception:
                pass

        # ---- Feishu calendar ----
        if feishu_syncer:
            try:
                r = feishu_syncer.create_event(
                    summary=title,
                    start_ts=int(start_dt.timestamp()),
                    end_ts=int(end_dt.timestamp()),
                    description=f"自动同步自学习计划 ({topic})")
                if r["ok"]:
                    result["feishu_created"] += 1
                else:
                    result["feishu_errors"].append(r.get("error", ""))
            except Exception as e:
                result["feishu_errors"].append(str(e)[:100])

    return result


def sync_plan_to_calendar(plan, *, kind: str = "review", topic: str = "",
                          slot_time: str = "20:00", local: bool = True,
                          feishu: bool = False, now: Optional[int] = None
                          ) -> dict[str, Any]:
    """Dispatch to the right syncer based on plan kind.

    ``kind``: ``"review"`` (Demo B ReviewPlan) or ``"learning"`` (Demo C Plan).
    """
    if kind == "learning":
        return sync_demo_c_plan(plan, slot_time=slot_time, local=local,
                                feishu=feishu, now=now)
    return sync_review_plan(plan, topic=topic, slot_time=slot_time,
                            local=local, feishu=feishu, now=now)
