"""User-defined scheduled jobs (Phase 9 — GOAL.md 自定义定时任务).

Lets a user register arbitrary timed jobs ("每天8点提醒我背单词", "3天后提醒我
交作业", "每周日发我周报") that fire at a specified time and push a custom
message to a channel. Reuses the existing 60s scheduler loop + push layer.

Rule syntax (simple, cron-like but friendlier):
- ``"daily 08:00"``        — every day at 08:00
- ``"weekly 0 20:00"``     — every week, day-of-week 0 (Mon) at 20:00
- ``"once 2026-07-12T09:00"`` — one-off at an exact datetime

Storage mirrors ``calendar_store.py``'s JSON-file convention (``~/.campus/jobs.json``).
Pure rule evaluation (``due_jobs``) with now-injection, matching the codebase
convention. No cron library — stdlib only.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import time
from typing import Any, Optional

from campus.runtime.paths import state_dir

__all__ = ["Job", "JobStore", "due_jobs", "parse_rule"]

_DEFAULT_PATH = os.path.join(state_dir(), "jobs.json")


class Job:
    """A user-defined scheduled job (plain dict for JSON-friendliness)."""
    def __init__(self, *, id: str, message: str, rule: str,
                 channel: str = "feishu", target: str = "",
                 enabled: bool = True, last_fired: int = 0,
                 created_at: int = 0) -> None:
        self.id = id
        self.message = message
        self.rule = rule
        self.channel = channel
        self.target = target
        self.enabled = enabled
        self.last_fired = last_fired
        self.created_at = created_at

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Job":
        return cls(id=d.get("id", ""), message=d.get("message", ""),
                   rule=d.get("rule", ""), channel=d.get("channel", "feishu"),
                   target=d.get("target", ""), enabled=d.get("enabled", True),
                   last_fired=d.get("last_fired", 0),
                   created_at=d.get("created_at", 0))


class JobStore:
    """JSON-file store for user jobs (mirrors calendar_store pattern)."""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path or _DEFAULT_PATH

    def _all(self) -> list[dict[str, Any]]:
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, jobs: list[dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)

    def list(self) -> list[dict[str, Any]]:
        return self._all()

    def add(self, *, message: str, rule: str, channel: str = "feishu",
            target: str = "", now: Optional[int] = None) -> dict[str, Any]:
        now = int(now if now is not None else time.time())
        job = Job(id=f"job_{now}_{os.urandom(4).hex()}", message=message,
                  rule=rule, channel=channel, target=target, created_at=now)
        jobs = self._all()
        jobs.append(job.to_dict())
        self._save(jobs)
        return job.to_dict()

    def delete(self, job_id: str) -> bool:
        jobs = self._all()
        new = [j for j in jobs if j.get("id") != job_id]
        if len(new) == len(jobs):
            return False
        self._save(new)
        return True

    def update_last_fired(self, job_id: str, ts: int) -> None:
        jobs = self._all()
        for j in jobs:
            if j.get("id") == job_id:
                j["last_fired"] = ts
                break
        self._save(jobs)


def parse_rule(rule: str) -> dict[str, Any]:
    """Parse a rule string into ``{type, time, weekday, datetime}``.

    Returns ``{"type": "invalid", "error": ...}`` on bad input.
    """
    r = (rule or "").strip().lower()
    if not r:
        return {"type": "invalid", "error": "empty rule"}

    # once <ISO datetime>
    m = re.match(r"^once\s+(\d{4}-\d{2}-\d{2}[t ]\d{2}:\d{2})", r)
    if m:
        try:
            dt = _dt.datetime.fromisoformat(m.group(1).replace(" ", "T"))
            return {"type": "once", "datetime": dt}
        except Exception as e:
            return {"type": "invalid", "error": str(e)}

    # daily <HH:MM>
    m = re.match(r"^daily\s+(\d{1,2}):(\d{2})", r)
    if m:
        return {"type": "daily", "hour": int(m.group(1)),
                "minute": int(m.group(2))}

    # weekly <weekday 0-6> <HH:MM>
    m = re.match(r"^weekly\s+([0-6])\s+(\d{1,2}):(\d{2})", r)
    if m:
        return {"type": "weekly", "weekday": int(m.group(1)),
                "hour": int(m.group(2)), "minute": int(m.group(3))}

    return {"type": "invalid", "error": f"unrecognized rule: {rule}"}


def due_jobs(jobs: list[dict[str, Any]], now: _dt.datetime) -> list[dict[str, Any]]:
    """Return jobs that are due at ``now`` (and haven't fired yet today/this slot).

    A job is "due" if:
    - ``enabled`` and the rule matches ``now``'s time, AND
    - it hasn't already fired in this matching window (``last_fired`` guard).
    """
    out = []
    now_ts = int(now.timestamp())
    for j in jobs:
        if not j.get("enabled", True):
            continue
        parsed = parse_rule(j.get("rule", ""))
        due = False
        if parsed["type"] == "daily":
            if now.hour == parsed["hour"] and now.minute == parsed["minute"]:
                due = True
        elif parsed["type"] == "weekly":
            if (now.weekday() == parsed["weekday"] and
                    now.hour == parsed["hour"] and now.minute == parsed["minute"]):
                due = True
        elif parsed["type"] == "once":
            dt = parsed["datetime"]
            # fire within the current minute
            if (dt.year == now.year and dt.month == now.month and
                    dt.day == now.day and dt.hour == now.hour and
                    dt.minute == now.minute):
                due = True
        if not due:
            continue
        # dedup: don't fire twice in the same minute
        last = j.get("last_fired", 0)
        if last and (now_ts - last) < 120:  # 2-min dedup window
            continue
        out.append(j)
    return out
