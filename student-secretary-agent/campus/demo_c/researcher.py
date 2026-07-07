"""Researcher: find learning resources for a goal (LLM, structured output)."""
from __future__ import annotations
import argparse, json
from typing import List
from .types import Resource
from ._llm import ask_llm, extract_json

PROMPT_TMPL = (
    "You are an expert learning-resource curator. For the goal below, suggest up to {n} "
    "high-quality, well-known, FREE resources (courses/books/docs/videos). Prefer authoritative "
    "providers (universities, established open-source projects). Return ONLY minified JSON, no prose, "
    "no code fence, exactly: "
    "{{\"resources\":[{{\"title\":\"...\",\"url\":\"...\",\"source_type\":\"course|doc|video|blog\","
    "\"provider\":\"...\",\"year\":2024,\"est_minutes\":600,\"difficulty\":\"beginner\"}}]}}\n"
    "Learning goal: {goal}"
)

VALID_STYPES = {"course", "doc", "video", "blog"}
VALID_DIFF = {"beginner", "intermediate", "advanced"}


def parse_resources(raw) -> List[Resource]:
    """Parse LLM output into Resource list. Pure / unit-testable; drops invalid rows."""
    data = extract_json(raw) if raw else None
    if isinstance(data, dict) and isinstance(data.get("resources"), list):
        items = data["resources"]
    elif isinstance(data, list):
        items = data
    else:
        return []
    out: List[Resource] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        stype = (str(item.get("source_type") or "doc")).strip().lower()
        if stype not in VALID_STYPES:
            stype = "doc"
        diff = (str(item.get("difficulty") or "beginner")).strip().lower()
        if diff not in VALID_DIFF:
            diff = "beginner"
        year = None
        try:
            year = int(item.get("year")) if item.get("year") else None
        except Exception:
            year = None
        em = 0
        try:
            em = int(item.get("est_minutes") or 0)
        except Exception:
            em = 0
        out.append(Resource(
            title=title,
            url=str(item.get("url") or "about:blank").strip(),
            source_type=stype,
            provider=str(item.get("provider") or "").strip(),
            year=year, est_minutes=em, difficulty=diff,
        ))
    return out


def search_resources(goal, top_k=6, model="glm-4.6") -> List[Resource]:
    text, rc = ask_llm(PROMPT_TMPL.format(n=top_k, goal=goal), model=model)
    return parse_resources(text)


def _main():
    ap = argparse.ArgumentParser(description="Find learning resources for a goal (GLM).")
    ap.add_argument("goal")
    ap.add_argument("-n", type=int, default=6)
    args = ap.parse_args()
    res = search_resources(args.goal, args.n)
    print(json.dumps([r.__dict__ for r in res], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()
