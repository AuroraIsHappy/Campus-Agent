"""Skill discovery + reliability scoring (architecture §4.4).

Given a fuzzy user need, search the catalog, rank by (match strength * reliability),
and pick an execution mode. Reliability comes from ``SkillEntry.reliability()``; match
uses the shared CJK-aware tokenizer so Chinese needs match Chinese categories.
"""
from __future__ import annotations
from typing import Optional

from campus.memory.embedding import tokenize
from campus.meta_agent.skill_pack import load_skill_pack
from campus.meta_agent.types import SkillEntry

__all__ = ["SkillRegistry", "reliability_score"]


def reliability_score(entry: SkillEntry) -> float:
    return entry.reliability()


class SkillRegistry:
    """Search + rank skills from a catalog (default: the bundled skill pack)."""

    def __init__(self, skills: Optional[list[SkillEntry]] = None) -> None:
        self.skills = list(skills) if skills is not None else load_skill_pack()

    def _hay(self, entry: SkillEntry) -> set[str]:
        return set(tokenize(f"{entry.name} {entry.category} {entry.description} {entry.source}"))

    def search(self, need: str) -> list[SkillEntry]:
        """Plain overlap search (no reliability weighting), strongest overlap first."""
        q = set(tokenize(need))
        if not q:
            return []
        scored = []
        for s in self.skills:
            overlap = len(q & self._hay(s))
            if overlap > 0:
                scored.append((overlap, s))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [s for _, s in scored]

    def discover(self, need: str, k: int = 5) -> list[tuple[SkillEntry, float]]:
        """Rank by match-strength * reliability. Returns [(entry, score)] desc."""
        q = set(tokenize(need))
        if not q:
            return []
        ranked = []
        for s in self.skills:
            overlap = len(q & self._hay(s))
            if overlap == 0:
                continue
            strength = overlap / len(q)
            ranked.append((s, round(strength * s.reliability(), 4)))
        ranked.sort(key=lambda t: t[1], reverse=True)
        return ranked[:k]

    def best(self, need: str) -> Optional[SkillEntry]:
        d = self.discover(need, k=1)
        return d[0][0] if d else None

    def pick_mode(self, entry: SkillEntry) -> str:
        """How to execute a chosen skill: direct if installed, else install/compose."""
        if entry.installed:
            return "direct"
        if entry.source == "cli_anything":
            return "install_or_compose"
        return "compose"
