"""SourceRanker: heuristic score + pick the best resource for the goal."""
from __future__ import annotations
import argparse, json, re
from typing import List
from .types import Resource, RankedPick, RankedResult

AUTHORITY = ("mit", "stanford", "berkeley", "harvard", "university", "college", "ocw", "csail")
OFFICIAL = ("official", "documentation", "docs", "guide", "tutorial", "handbook")


def _tokens(s: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 2]


def score(resource: Resource, goal: str) -> float:
    """Heuristic 0..1: topic overlap + authority + recency + level fit."""
    s = 0.30
    overlap = len(set(_tokens(goal)) & (set(_tokens(resource.title)) | set(_tokens(resource.provider))))
    s += min(0.25, 0.05 * overlap)
    blob = (resource.provider + " " + resource.title).lower()
    if any(a in blob for a in AUTHORITY):
        s += 0.20
    if any(a in blob for a in OFFICIAL):
        s += 0.08
    if resource.year and resource.year >= 2020:
        s += 0.10
    if resource.year and resource.year < 2015:
        s -= 0.15  # outdated
    if resource.difficulty == "beginner":
        s += 0.05
    if resource.source_type in ("course", "doc"):
        s += 0.05
    return round(min(1.0, s), 3)


def _explain(resource: Resource, goal: str, sc: float) -> List[str]:
    reasons = ["综合评分 %.2f" % sc]
    blob = (resource.provider + " " + resource.title).lower()
    if any(a in blob for a in AUTHORITY):
        reasons.append("权威学术机构/官方出品")
    if resource.year and resource.year >= 2020:
        reasons.append("内容较新 (%d)" % resource.year)
    if resource.difficulty == "beginner":
        reasons.append("难度友好, 适合入门")
    if resource.source_type in ("course", "doc"):
        reasons.append("形式为 %s, 系统化" % resource.source_type)
    return reasons


def rank(resources: List[Resource], goal: str) -> RankedResult:
    picks = sorted((RankedPick(resource=r, score=score(r, goal)) for r in resources),
                   key=lambda p: p.score, reverse=True)
    if picks:
        picks[0].reasons = _explain(picks[0].resource, goal, picks[0].score)
    return RankedResult(goal=goal, recommendation=picks[0] if picks else None, picks=picks)


def _main():
    ap = argparse.ArgumentParser(description="Rank researcher candidates for a goal.")
    ap.add_argument("--goal", required=True)
    ap.add_argument("--candidates", required=True, help="JSON file from researcher")
    args = ap.parse_args()
    data = json.load(open(args.candidates, encoding="utf-8"))
    resources = [Resource(**d) for d in data]
    result = rank(resources, args.goal)
    print(json.dumps({
        "goal": result.goal,
        "recommendation": {"title": result.recommendation.resource.title,
                           "url": result.recommendation.resource.url,
                           "score": result.recommendation.score,
                           "reasons": result.recommendation.reasons} if result.recommendation else None,
        "all": [{"title": p.resource.title, "score": p.score} for p in result.picks],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()
