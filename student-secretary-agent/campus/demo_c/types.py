"""Data shapes for the Demo C learning-plan chain (Phase 1)."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, List

SOURCE_TYPES = {"course", "doc", "video", "blog"}
DIFFICULTIES = {"beginner", "intermediate", "advanced"}
NL = chr(10)


@dataclass
class Resource:
    title: str
    url: str
    source_type: str = "doc"
    provider: str = ""
    year: Optional[int] = None
    est_minutes: int = 0
    difficulty: str = "beginner"

    def __post_init__(self):
        if self.source_type not in SOURCE_TYPES:
            raise ValueError("source_type must be in " + str(SOURCE_TYPES))
        if self.difficulty not in DIFFICULTIES:
            raise ValueError("difficulty must be in " + str(DIFFICULTIES))


@dataclass
class RankedPick:
    resource: Resource
    score: float = 0.0
    reasons: List[str] = field(default_factory=list)


@dataclass
class RankedResult:
    goal: str
    recommendation: RankedPick
    picks: List[RankedPick] = field(default_factory=list)


@dataclass
class DayTask:
    n: int
    date: str
    topic: str
    est_minutes: int = 20
    done: bool = False


@dataclass
class Plan:
    goal: str
    resource_title: str
    resource_url: str
    slot_time: str = "20:00"
    slot_minutes: int = 20
    days: List[DayTask] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = ["# 学习计划: " + self.goal, "",
                 "**推荐资源**: [" + self.resource_title + "](" + self.resource_url + ")",
                 "**节奏**: 每天 " + self.slot_time + " - " + str(self.slot_minutes) + " 分钟 - 共 " + str(len(self.days)) + " 天", "",
                 "| Day | 日期 | 主题 | 时长 |", "|---|---|---|---|"]
        for d in self.days:
            lines.append("| " + str(d.n) + " | " + d.date + " | " + d.topic + " | " + str(d.est_minutes) + "m |")
        return NL.join(lines)


@dataclass
class QuizQuestion:
    q: str
    answer: str
    explanation: str = ""
    options: Optional[List[str]] = None


@dataclass
class Quiz:
    day: int
    topic: str
    questions: List[QuizQuestion] = field(default_factory=list)


def to_dict(obj):
    if isinstance(obj, list):
        return [to_dict(x) for x in obj]
    if hasattr(obj, "__dataclass_fields__"):
        return {k: to_dict(v) for k, v in asdict(obj).items()}
    return obj
