"""Quality gates for Demo B (B-F1..B-F6 / B-Q1..B-Q3).

Each ``check_*`` returns a ``CheckResult`` (name / passed / detail) so the
pipeline can attach a uniform evidence list to ``Verification.md``. Mirrors
``campus.demo_a.checkers``.
"""
from __future__ import annotations

from campus.demo_b.types import (
    CheckResult, ExtractedText, KnowledgeGraph, ReviewPlan, Quiz,
    MIN_RESOURCES, EXTRACTION_RATE_MIN,
)
from campus.demo_b import knowledge_graph as _kg
from campus.demo_b import extractors as _ex

__all__ = [
    "check_extraction", "check_kg", "check_resources",
    "check_plan_covers", "check_plan_budget", "check_quiz", "all_checks",
]


def check_extraction(results: list[ExtractedText],
                    minimum: float = EXTRACTION_RATE_MIN) -> CheckResult:
    rate, ok = _ex.extraction_rate(results, minimum)
    return CheckResult(
        name="B-F1 extraction_rate",
        passed=bool(results) and ok,
        detail=f"rate={rate:.2f} (min {minimum:.2f}); {len(results)} file(s)",
    )


def check_kg(kg: KnowledgeGraph) -> CheckResult:
    issues = _kg.validate_kg(kg)
    passed = len(kg.nodes) > 0 and not issues
    return CheckResult(
        name="B-F2 knowledge_graph",
        passed=passed,
        detail=f"{len(kg.nodes)} node(s), {len(kg.valid_edges())} valid edge(s); "
               f"issues={issues or 'none'}",
    )


def check_resources(candidates: list, minimum: int = MIN_RESOURCES) -> CheckResult:
    n = len(candidates or [])
    return CheckResult(
        name="B-F3 resources",
        passed=n >= minimum,
        detail=f"{n} candidate(s) (min {minimum})",
    )


def check_plan_covers(plan: ReviewPlan) -> CheckResult:
    passed = bool(plan.days) and plan.days[-1].date <= plan.exam_date
    last = plan.days[-1].date if plan.days else "-"
    return CheckResult(
        name="B-F4 plan_covers_to_exam",
        passed=passed,
        detail=f"{len(plan.days)} day(s); last={last} exam={plan.exam_date}",
    )


def check_plan_budget(plan: ReviewPlan) -> CheckResult:
    return CheckResult(
        name="B-Q3 plan_within_budget",
        passed=plan.within_budget,
        detail=f"total={plan.total_minutes}m <= free={plan.free_minutes}m",
    )


def check_quiz(quiz: Quiz | None) -> CheckResult:
    n = len(quiz.questions) if quiz else 0
    return CheckResult(
        name="B-F5 daily_quiz",
        passed=n >= 1,
        detail=f"{n} question(s)",
    )


def all_checks(*, results, kg, candidates, plan, day1_quiz) -> list[CheckResult]:
    """Run the full Demo B gate set (used by pipeline + e2e test)."""
    return [
        check_extraction(results),
        check_kg(kg),
        check_resources(candidates),
        check_plan_covers(plan),
        check_plan_budget(plan),
        check_quiz(day1_quiz),
    ]
