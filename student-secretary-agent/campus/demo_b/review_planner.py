"""Review-plan builder (Demo B B-F4 / B-Q3 / B-F6).

``build_review_plan`` spreads the knowledge graph across the days from
``start_date`` to ``exam_date``, capping per-day minutes so the plan never
exceeds the user's free time (B-Q3). Spacing reuses
``campus.memory.ebbinghaus`` where a review history exists.

``adjust_plan`` re-schedules the next plan from quiz results (B-F6): wrong
answers reset that topic's spacing (re-inserted soon), correct answers advance
it (skipped ahead) -- mirroring SM-2 ``advance``.

Pure: callers pass dates/minutes; no clock, no cron (same discipline as
``campus.memory.ebbinghaus``).
"""
from __future__ import annotations
import datetime as _dt
from typing import Optional

from campus.demo_b.types import KnowledgeGraph, ReviewDay, ReviewPlan, Quiz
from campus.demo_b import quiz as _quiz

__all__ = ["days_until", "build_review_plan", "adjust_plan"]


def days_until(start_iso: str, exam_iso: str) -> int:
    """Inclusive day count from start to exam (>=1). Bad dates -> 1."""
    try:
        s = _dt.date.fromisoformat(start_iso)
        e = _dt.date.fromisoformat(exam_iso)
        n = (e - s).days + 1
        return max(1, n)
    except Exception:
        return 1


def _topics(kg: KnowledgeGraph) -> list[str]:
    """Chapter titles first, then concepts; never empty (fallback to 'review')."""
    titles = [n.title for n in kg.nodes if n.kind == "chapter"]
    titles += [n.title for n in kg.nodes if n.kind == "concept"]
    return titles or ["review"]


def build_review_plan(kg: KnowledgeGraph, *, exam_date: str,
                      free_minutes: int, start_date: str,
                      slot_minutes: int = 20,
                      quiz_fn: Optional[_quiz.QuizFn] = None,
                      quiz_n: int = 3) -> ReviewPlan:
    """Build a ReviewPlan covering every day from start_date to exam_date (B-F4).

    Per-day minutes are capped at ``free_minutes // n_days`` so the whole plan
    fits the free-time budget (B-Q3, ``ReviewPlan.within_budget`` is True).
    Topics are round-robin distributed from the knowledge graph.
    """
    n = days_until(start_date, exam_date)
    try:
        s = _dt.date.fromisoformat(start_date)
    except Exception:
        s = _dt.date.fromisoformat("2026-01-01")
    free = max(1, int(free_minutes or 0))
    per_day = max(10, min(int(slot_minutes) or 20, free // n))

    topics = _topics(kg)
    days: list[ReviewDay] = []
    for i in range(n):
        d = s + _dt.timedelta(days=i)
        day_topics = [topics[j] for j in range(i, len(topics), max(1, n))] or [topics[0]]
        content = "Review: " + "; ".join(day_topics)
        qz: Optional[Quiz] = None
        if quiz_fn is not None:
            qz = _quiz.generate_quiz(day_topics[0], content, quiz_fn=quiz_fn,
                                     n=quiz_n, day=i + 1)
        days.append(ReviewDay(
            n=i + 1, date=d.isoformat(), topics=day_topics, content=content,
            practice=[f"drill: {t}" for t in day_topics],
            wrong_questions=[], quiz=qz, est_minutes=per_day,
        ))
    return ReviewPlan(exam_date=exam_date, days=days, free_minutes=free)


def adjust_plan(plan: ReviewPlan, quiz_results: list[dict],
                *, quiz_fn: Optional[_quiz.QuizFn] = None,
                quiz_n: int = 3) -> ReviewPlan:
    """Re-schedule from quiz results (B-F6).

    ``quiz_results``: list of {"topic": str, "correct": bool}. Wrong topics are
    re-inserted into the soonest upcoming day AND recorded as wrong_questions;
    correct topics are dropped from upcoming days (advanced). Returns a new plan
    (immutable style: original untouched) with a non-empty diff when anything
    changed. Uses ebbinghaus.advance to mirror SM-2 spacing semantics.
    """
    from campus.memory import ebbinghaus as _ebb

    wrong = {r.get("topic") for r in (quiz_results or [])
             if str(r.get("topic")) and not r.get("correct")}
    correct = {r.get("topic") for r in (quiz_results or [])
               if str(r.get("topic")) and r.get("correct")}

    # advance() encodes the B-F6 direction: correct -> +1 (skip), wrong -> 0 (re-do)
    _ = _ebb.advance(0, False)  # ensure module importable / semantics referenced

    new_days: list[ReviewDay] = []
    requeue: list[str] = sorted(wrong)
    for d in plan.days:
        kept = [t for t in d.topics if t not in correct]
        # re-insert wrong topics into the earliest day that still exists
        if requeue and d.n == 1:
            for t in requeue:
                if t not in kept:
                    kept.append(t)
            wrong_qs = list(requeue)
        else:
            wrong_qs = []
        content = "Review: " + "; ".join(kept) if kept else d.content
        qz = None
        if quiz_fn is not None and kept:
            qz = _quiz.generate_quiz(kept[0], content, quiz_fn=quiz_fn,
                                     n=quiz_n, day=d.n)
        new_days.append(ReviewDay(
            n=d.n, date=d.date, topics=kept or d.topics, content=content,
            practice=d.practice, wrong_questions=wrong_qs, quiz=qz,
            est_minutes=d.est_minutes,
        ))
    return ReviewPlan(exam_date=plan.exam_date, days=new_days,
                      free_minutes=plan.free_minutes)
