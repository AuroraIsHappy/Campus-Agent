"""Scheduler: lay a resource out into an N-day study plan (deterministic)."""
from __future__ import annotations
import sys, argparse
from datetime import date, timedelta
from typing import List, Optional
from .types import Resource, Plan, DayTask


def build_plan(resource: Resource, goal: str, days: int = 30,
               slot_time: str = "20:00", slot_minutes: int = 20,
               start_date: Optional[date] = None, weekdays_only: bool = False,
               topics: Optional[List[str]] = None) -> Plan:
    start = start_date or date.today()
    if topics:
        seq = list(topics)
    else:
        seq = [f"{resource.title} · Part {i+1}" for i in range(max(days, 1))]
    tasks: List[DayTask] = []
    cur, n = start, 0
    while n < days:
        if weekdays_only and cur.weekday() >= 5:  # skip Sat(5)/Sun(6)
            cur += timedelta(days=1)
            continue
        topic = seq[n % len(seq)] if seq else f"{resource.title} · Part {n+1}"
        tasks.append(DayTask(n=n + 1, date=cur.isoformat(), topic=topic, est_minutes=slot_minutes))
        n += 1
        cur += timedelta(days=1)
    return Plan(goal=goal, resource_title=resource.title, resource_url=resource.url,
                slot_time=slot_time, slot_minutes=slot_minutes, days=tasks)


def _main():
    ap = argparse.ArgumentParser(description="Build an N-day study plan for a resource.")
    ap.add_argument("title")
    ap.add_argument("--url", default="https://example.com")
    ap.add_argument("--goal", default=None)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--time", default="20:00")
    ap.add_argument("--minutes", type=int, default=20)
    ap.add_argument("--weekdays-only", action="store_true")
    args = ap.parse_args()
    res = Resource(title=args.title, url=args.url)
    plan = build_plan(res, goal=args.goal or args.title, days=args.days,
                      slot_time=args.time, slot_minutes=args.minutes,
                      weekdays_only=args.weekdays_only)
    print(plan.to_markdown())


if __name__ == "__main__":
    _main()
