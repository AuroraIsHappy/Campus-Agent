"""Meta-Agent (architecture §4.4) — ties memory + routing + discovery together.

Classifies an incoming task (short -> Hermes direct, long -> Odyssey role DAG),
recommends skills, and emits a role DAG with ``parents`` wiring (consumable by the
Phase 2/3 orchestrator). Deterministic: no LLM; classification is keyword + length
heuristic, refinable later via an injected classifier.
"""
from __future__ import annotations
from typing import Optional

from campus.meta_agent.skill_discovery import SkillRegistry
from campus.meta_agent.types import ClassifyDecision

__all__ = ["MetaAgent", "LONG_KEYWORDS", "LONG_DAG"]

# Cues that a need is long-horizon (multi-step, high-stakes) -> Odyssey DAG.
LONG_KEYWORDS = (
    "策划案", "复习计划", "学习计划", "外联", "调研报告", "期末复习",
    "社会实践", "讲义", "知识图谱", "邮件草稿", "参观", "实习",
    # Phase 9: English equivalents so English fuzzy requests also go long-horizon
    "review plan", "study plan", "exam", "machine learning", "lecture notes",
    "knowledge graph", "literature review", "research project", "internship",
)

# Long-task Odyssey role DAG (mirrors demo_a pipeline §3). critic debates planner;
# reviewer debates writer; the rest chain. parents reference earlier roles -> acyclic.
LONG_DAG: list[dict] = [
    {"role": "planner", "parents": ()},
    {"role": "critic", "parents": ("planner",)},
    {"role": "researcher", "parents": ("planner",)},
    {"role": "source_verifier", "parents": ("researcher",)},
    {"role": "source_ranker", "parents": ("source_verifier",)},
    {"role": "writer", "parents": ("source_ranker",)},
    {"role": "reviewer", "parents": ("writer",)},
    {"role": "email", "parents": ("writer",)},
]

_SHORT_THRESHOLD_CHARS = 20


class MetaAgent:
    def __init__(self, memory=None, skill_registry: Optional[SkillRegistry] = None,
                 routing_config=None) -> None:
        self.memory = memory
        self.skills = skill_registry or SkillRegistry()
        self.routing = routing_config

    def classify(self, task: str) -> ClassifyDecision:
        text = task or ""
        is_long = len(text) > _SHORT_THRESHOLD_CHARS or any(k in text for k in LONG_KEYWORDS)
        kind = "long" if is_long else "short"
        skills = [s.name for s, _ in self.skills.discover(text, k=3)]
        reason = ("多步骤/长程需求 → Odyssey 角色 DAG" if is_long
                  else "单步短任务 → Hermes 直达")
        return ClassifyDecision(kind=kind, reason=reason, skills=skills)

    def recommend_skills(self, need: str, k: int = 5) -> list[str]:
        return [s.name for s, _ in self.skills.discover(need, k=k)]

    def build_dag(self, decision: ClassifyDecision) -> list[dict]:
        """Map a classification to an executable DAG.

        short -> one ``hermes_direct`` node carrying the recommended skills.
        long  -> the Odyssey role DAG (parents-encoded, acyclic).
        """
        if decision.kind == "short":
            return [{"role": "hermes_direct", "parents": (), "skills": list(decision.skills)}]
        return [dict(node) for node in LONG_DAG]
