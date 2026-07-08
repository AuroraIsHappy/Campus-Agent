"""Quiz generator for review days (Demo B B-F5).

``generate_quiz`` turns a day's content into a ``Quiz``. The question generator
is an injectable ``quiz_fn``: the default is a deterministic stub (turns key
lines into "What is X?" items) good enough for tests; a real LLM quiz writer
plugs in here. Mirrors campus/demo_c/quiz.py shape.
"""
from __future__ import annotations
from typing import Callable, Optional

from campus.demo_b.types import Quiz, QuizQ

__all__ = ["QuizFn", "default_quiz_fn", "generate_quiz"]

# quiz_fn(topic, content, n) -> list[QuizQ]
QuizFn = Callable[[str, str, int], list[QuizQ]]


def default_quiz_fn(topic: str, content: str, n: int) -> list[QuizQ]:
    """Deterministic stub: derive n questions from non-empty content lines.

    Production injects an LLM-backed quiz_fn. Always returns well-formed QuizQs
    so the pipeline has something concrete to schedule in tests.
    """
    lines = [ln.strip("-*• ").strip() for ln in (content or "").splitlines()
             if ln.strip()]
    picks = lines[:n] if lines else [topic or "review"]
    out: list[QuizQ] = []
    for i, p in enumerate(picks, 1):
        out.append(QuizQ(q=f"Q{i}: explain {p} (topic: {topic}).",
                         answer=p,
                         explanation=f"Key point from the lecture on {topic}."))
    return out


def generate_quiz(topic: str, content: str, *,
                  quiz_fn: Optional[QuizFn] = None, n: int = 3,
                  day: int = 1) -> Quiz:
    """Build a Quiz for one review day (B-F5). Never raises; empty -> 1 placeholder."""
    fn = quiz_fn or default_quiz_fn
    try:
        qs = fn(topic, content, n) or []
    except Exception:
        qs = []
    if not qs:
        qs = [QuizQ(q=f"What is the core idea of {topic}?", answer=topic)]
    return Quiz(day=day, topic=topic, questions=qs[:max(1, n)])
