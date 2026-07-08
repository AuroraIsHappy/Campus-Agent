"""Data shapes for the Demo B lecture-review chain (Phase 5).

Mirrors the demo_c/demo_a dataclass style: frozen-friendly dataclasses with
``__post_init__`` validation + a ``to_dict`` helper. Pure stdlib (no LLM, no
network) so unit tests need no Hermes / no model / no filesystem.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional

__all__ = [
    "KG_KINDS", "EXTRACTION_RATE_MIN", "MIN_RESOURCES",
    "LectureDoc", "ExtractedText", "KGNode", "KGEdge", "KnowledgeGraph",
    "QuizQ", "Quiz", "ReviewDay", "ReviewPlan",
    "CheckResult", "RunResult", "to_dict",
]

# knowledge-graph node kinds (architecture §Phase5 / B-F2)
KG_KINDS = ("chapter", "concept", "formula", "question_type", "key_point")

# deterministic quality thresholds (B-F1 / B-F3)
EXTRACTION_RATE_MIN = 0.5     # at least half of scanned files extract successfully
MIN_RESOURCES = 3             # B-F3: >=3 external resource candidates


@dataclass
class LectureDoc:
    """A scanned lecture file on disk (PDF/PPT/MD/DOCX/TXT)."""
    path: str
    ext: str                       # lower-cased, no dot, e.g. 'pdf'
    size_bytes: int = 0


@dataclass
class ExtractedText:
    """Text pulled out of one ``LectureDoc`` (B-F1). ``ok=False`` on failure."""
    doc: LectureDoc
    text: str = ""
    ok: bool = True
    error: str = ""

    @property
    def chars(self) -> int:
        return len(self.text or "")


@dataclass
class KGNode:
    """One node of the knowledge graph (chapter / concept / formula / ...)."""
    id: str
    kind: str
    title: str
    summary: str = ""
    source_doc: str = ""
    refs: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.kind not in KG_KINDS:
            raise ValueError("kind must be in " + str(KG_KINDS))
        if not self.title:
            raise ValueError("title is required")


@dataclass
class KGEdge:
    """A typed relationship between two KG nodes (ids must exist in the graph)."""
    src: str
    dst: str
    rel: str = "related"


@dataclass
class KnowledgeGraph:
    """Structured knowledge extracted from the lecture corpus (B-F2)."""
    nodes: list[KGNode] = field(default_factory=list)
    edges: list[KGEdge] = field(default_factory=list)
    source_docs: list[str] = field(default_factory=list)

    @property
    def node_ids(self) -> set[str]:
        return {n.id for n in self.nodes}

    def valid_edges(self) -> list[KGEdge]:
        """Edges whose endpoints both exist (used by checkers B-F2)."""
        ids = self.node_ids
        return [e for e in self.edges if e.src in ids and e.dst in ids]


@dataclass
class QuizQ:
    q: str
    answer: str
    explanation: str = ""
    options: Optional[list[str]] = None


@dataclass
class Quiz:
    day: int
    topic: str
    questions: list[QuizQ] = field(default_factory=list)


@dataclass
class ReviewDay:
    """One day of the review plan (B-F4)."""
    n: int
    date: str                       # ISO yyyy-mm-dd
    topics: list[str] = field(default_factory=list)
    content: str = ""
    practice: list[str] = field(default_factory=list)
    wrong_questions: list[str] = field(default_factory=list)
    quiz: Optional[Quiz] = None
    est_minutes: int = 20


@dataclass
class ReviewPlan:
    """Full review plan up to the exam date (B-F4 / B-Q3)."""
    exam_date: str
    days: list[ReviewDay] = field(default_factory=list)
    free_minutes: int = 0

    @property
    def total_minutes(self) -> int:
        return sum(d.est_minutes for d in self.days)

    @property
    def within_budget(self) -> bool:
        """B-Q3: planned time must not exceed free time."""
        return self.total_minutes <= self.free_minutes


@dataclass
class CheckResult:
    """One quality-gate outcome (mirrors demo_a.checkers.CheckResult)."""
    name: str
    passed: bool
    detail: str = ""


@dataclass
class RunResult:
    """End-to-end Demo B outcome (mirrors demo_a.RunResult)."""
    ok: bool
    run_dir: str = ""
    final_status: str = ""
    extraction_rate: float = 0.0
    kg_nodes: int = 0
    resource_count: int = 0
    plan_days: int = 0
    checks: list[CheckResult] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    error: str = ""


def to_dict(obj):
    """Recursive dataclass -> dict (mirrors demo_c.types.to_dict)."""
    if isinstance(obj, list):
        return [to_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    if hasattr(obj, "__dataclass_fields__"):
        return {k: to_dict(v) for k, v in asdict(obj).items()}
    return obj
