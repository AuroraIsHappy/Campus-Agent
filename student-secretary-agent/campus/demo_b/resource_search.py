"""External resource search + reliability ranking (Demo B B-F3 / B-Q1).

Reuses ``campus.demo_c.types.Resource`` (same shape as Demo C) and
``campus.demo_c.ranker.score`` for explainable reliability scoring (year,
authority, topic match) so Demo B does not reinvent Demo C's ranker.

The actual web search is an injectable ``searcher``: the default is a
deterministic stub returning canned candidates (tests); a real Exa/browser
searcher plugs in here without changing the caller.
"""
from __future__ import annotations
from typing import Callable, Optional

from campus.demo_c.types import Resource
from campus.demo_b.types import MIN_RESOURCES

__all__ = ["Searcher", "default_searcher", "search_resources", "rank_resources"]

# searcher(topic) -> list[Resource]
Searcher = Callable[[str], list[Resource]]


def default_searcher(topic: str) -> list[Resource]:
    """Deterministic stub: a small canned corpus biased toward ``topic``.

    Mirrors the kind of output a real searcher returns (university courses,
    docs, repos) so the pipeline can be exercised end-to-end without network.
    """
    base = [
        Resource(title=f"{topic} — University Course", url="https://example.edu/courses/1",
                 source_type="course", provider="Example University", year=2024,
                 difficulty="intermediate"),
        Resource(title=f"{topic} — Official Documentation", url="https://example.org/docs",
                 source_type="doc", provider="Official", year=2024, difficulty="beginner"),
        Resource(title=f"{topic} — Lecture Notes (public)", url="https://example.edu/notes",
                 source_type="course", provider="Example University", year=2023,
                 difficulty="intermediate"),
        Resource(title=f"{topic} — Problem Set Repository", url="https://github.com/example/repo",
                 source_type="doc", provider="GitHub", year=2022, difficulty="advanced"),
        Resource(title="Unrelated Blog Post", url="https://blog.example.com/x",
                 source_type="blog", provider="blog", year=2010, difficulty="advanced"),
    ]
    return base


def rank_resources(resources: list[Resource], topic: str) -> list[tuple[Resource, float]]:
    """Score + sort candidates by reliability (reuse demo_c.ranker.score, B-Q1).

    Returns [(resource, score)] desc. Falls back to a simple score if demo_c's
    ranker is unavailable, so this module never hard-fails on an import.
    """
    try:
        from campus.demo_c import ranker as _r
        scored = [(r, _r.score(r, topic)) for r in resources]
    except Exception:
        scored = [(r, _fallback_score(r, topic)) for r in resources]
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored


def _fallback_score(r: Resource, topic: str) -> float:
    s = 0.0
    if topic and topic.lower() in (r.title or "").lower():
        s += 2.0
    if r.source_type == "course":
        s += 1.5
    if r.source_type == "blog":
        s -= 1.0
    if r.year and r.year >= 2022:
        s += 0.5
    return s


def search_resources(topic: str, *,
                     searcher: Optional[Searcher] = None,
                     top_k: int = 6,
                     min_results: int = MIN_RESOURCES) -> list[Resource]:
    """Search + rank external resources for ``topic`` (B-F3). Returns top_k.

    De-dupes by url. The returned list is reliability-ranked (B-Q1). The caller
    (pipeline/checkers) asserts ``len >= min_results``.
    """
    fn = searcher or default_searcher
    try:
        raw = fn(topic) or []
    except Exception:
        raw = []
    seen: set[str] = set()
    uniq: list[Resource] = []
    for r in raw:
        if r.url in seen:
            continue
        seen.add(r.url)
        uniq.append(r)
    ranked = rank_resources(uniq, topic)
    out = [r for r, _s in ranked[:top_k]]
    _ = min_results  # threshold asserted by checkers
    return out
