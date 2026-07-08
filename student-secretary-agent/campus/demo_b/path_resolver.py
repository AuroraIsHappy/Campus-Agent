"""Fuzzy lecture-path resolver (Phase 9 — GOAL.md 模糊路径需求).

Resolves a user's natural-language path hint (e.g. "桌面上那个数据结构讲义")
to concrete files. Strategy:

1. Expand shorthand locations ("桌面"→~/Desktop, "文档"→~/Documents, "下载"→~/Downloads).
2. Glob supported lecture extensions under those dirs (recursive, shallow).
3. Score candidates by token overlap with the query.
4. Single candidate → resolved. Multiple → ``needs_clarify=True`` so the agent
   asks the user to confirm before running the full pipeline.

An optional LLM resolver (``make_llm_resolver_fn``) lets the model pick the best
candidate when scoring is ambiguous — mirrors the ``make_searcher`` factory
pattern in ``campus/demo_b/llm.py``.

Pure, no side effects beyond filesystem reads. Windows-aware (Desktop is
``C:\\Users\\<u>\\Desktop``).
"""
from __future__ import annotations
import os
import re
from typing import Any, Optional

from campus.demo_b.extractors import SUPPORTED_EXTS

__all__ = [
    "resolve_lecture_path", "candidate_files", "score_candidate",
    "make_llm_resolver_fn", "LOCATION_ALIASES",
]

# Chinese → filesystem location aliases (expanduser handles the rest).
LOCATION_ALIASES = {
    "桌面": "~/Desktop",
    "desktop": "~/Desktop",
    "文档": "~/Documents",
    "documents": "~/Documents",
    "下载": "~/Downloads",
    "downloads": "~/Downloads",
    "d盘": "D:/",
    "e盘": "E:/",
}


def _expand_locations(query: str) -> list[str]:
    """Return candidate base dirs hinted by the query, expanded to real paths."""
    q = query.lower()
    dirs: list[str] = []
    for alias, path in LOCATION_ALIASES.items():
        if alias in q:
            expanded = os.path.expanduser(path)
            if os.path.isdir(expanded):
                dirs.append(expanded)
    # Always include Desktop + Documents as a fallback when nothing matched
    if not dirs:
        for d in ("~/Desktop", "~/Documents"):
            p = os.path.expanduser(d)
            if os.path.isdir(p):
                dirs.append(p)
    return dirs


def _query_tokens(query: str) -> list[str]:
    """Extract meaningful tokens from a Chinese/mixed path query.

    Drops common filler words and location aliases so scoring focuses on the
    subject (e.g. "数据结构", "讲义").
    """
    q = query.lower()
    # strip location aliases
    for alias in LOCATION_ALIASES:
        q = q.replace(alias, " ")
    # strip punctuation / filler
    q = re.sub(r"[那个这个我的在把给对和与及,，。.!！？?了过着]", " ", q)
    tokens = [t for t in re.split(r"\s+", q) if len(t) >= 2]
    return tokens


def candidate_files(search_dirs: list[str], max_per_dir: int = 200) -> list[dict[str, Any]]:
    """Glob supported lecture files under ``search_dirs``."""
    out: list[dict[str, Any]] = []
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        count = 0
        for root, _dirs, files in os.walk(d):
            for name in sorted(files):
                ext = os.path.splitext(name)[1].lstrip(".").lower()
                if ext in SUPPORTED_EXTS:
                    full = os.path.join(root, name)
                    try:
                        size = os.path.getsize(full)
                    except OSError:
                        size = 0
                    out.append({"path": full, "name": name, "ext": ext,
                                "size": size, "dir": d})
                    count += 1
                    if count >= max_per_dir:
                        break
            if count >= max_per_dir:
                break
    return out


def score_candidate(cand: dict[str, Any], tokens: list[str]) -> int:
    """Score a candidate by token overlap with the query (substring match).

    Higher = better. Filename matches weigh more than path matches.
    """
    if not tokens:
        return 1  # no tokens → all candidates tie
    name = cand.get("name", "").lower()
    path = cand.get("path", "").lower()
    score = 0
    for t in tokens:
        if t in name:
            score += 3
        elif t in path:
            score += 1
    return score


def resolve_lecture_path(query: str, *,
                         search_dirs: Optional[list[str]] = None,
                         resolver_fn=None,
                         max_candidates: int = 8) -> dict[str, Any]:
    """Resolve a fuzzy path query to concrete files.

    Returns ``{"resolved": <path or None>, "candidates": [...], "needs_clarify":
    bool, "clarify_options": [...]}``.

    - 0 candidates → ``needs_clarify=False``, ``resolved=None`` (caller tells user
      nothing was found).
    - 1 candidate (or one clearly-best) → ``resolved=<path>``.
    - multiple plausible → ``needs_clarify=True`` with ``clarify_options``.
    - if ``resolver_fn`` (LLM) is provided and there are ties, it picks one.
    """
    tokens = _query_tokens(query)
    dirs = search_dirs or _expand_locations(query)
    cands = candidate_files(dirs)

    if not cands:
        return {"resolved": None, "candidates": [], "needs_clarify": False,
                "clarify_options": [], "tokens": tokens}

    # score + sort
    for c in cands:
        c["score"] = score_candidate(c, tokens)
    cands.sort(key=lambda c: c["score"], reverse=True)
    top_score = cands[0]["score"]

    # filter to plausible (score > 0), or keep all if everything is 0
    plausible = [c for c in cands if c["score"] > 0] or cands[:max_candidates]
    plausible = plausible[:max_candidates]

    # if the top candidate is a clear winner (strictly higher than #2), resolve
    if len(plausible) == 1 or (len(plausible) >= 2 and plausible[0]["score"] > plausible[1]["score"]):
        return {"resolved": plausible[0]["path"], "candidates": plausible,
                "needs_clarify": False, "clarify_options": [], "tokens": tokens}

    # tie — try LLM resolver if available
    if resolver_fn is not None:
        try:
            picked = resolver_fn(query, plausible)
            if isinstance(picked, dict) and picked.get("path"):
                return {"resolved": picked["path"], "candidates": plausible,
                        "needs_clarify": False, "clarify_options": [], "tokens": tokens}
        except Exception:
            pass

    # need user clarification
    options = [f"{c['name']}  ({c['path']})" for c in plausible]
    return {"resolved": None, "candidates": plausible, "needs_clarify": True,
            "clarify_options": options, "tokens": tokens}


def make_llm_resolver_fn(model: str = "glm-4.6", provider: str = "zai"):
    """Factory: an LLM-backed resolver that picks the best candidate from a tie.

    Mirrors ``campus.demo_b.llm.make_searcher`` — returns a closure
    ``fn(query, candidates) -> dict`` that asks the model to choose by index.
    Returns ``None`` if the LLM is unavailable (so the caller falls back to
    user-clarification).
    """
    from campus.runtime.llm_config import require_real_llm
    real, _status = require_real_llm("auto")
    if not real:
        return None

    def _resolve(query: str, candidates: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
        from campus.runtime.llm_turn import ask_llm, extract_json
        lines = [f"{i}: {c['name']} ({c['path']}, {c.get('ext','')})"
                 for i, c in enumerate(candidates)]
        prompt = (
            "用户想找的讲义文件是：" + query + "\n\n"
            "候选文件列表：\n" + "\n".join(lines) +
            "\n\n请选出最可能是用户想要的那一个。只返回 JSON：{\"index\": <数字>}。"
        )
        text, _rc = ask_llm(prompt, model=model, provider=provider)
        data = extract_json(text)
        if isinstance(data, dict) and "index" in data:
            idx = int(data["index"])
            if 0 <= idx < len(candidates):
                return candidates[idx]
        return None

    return _resolve
