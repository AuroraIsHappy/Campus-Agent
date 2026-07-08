"""Deterministic Demo C runner for offline demos."""
from __future__ import annotations

import json
import os
import datetime as dt

from campus.demo_c import ranker, scheduler
from campus.demo_c.types import Quiz, QuizQuestion, Resource, to_dict


def offline_resources(goal: str) -> list[Resource]:
    clean = goal.strip() or "目标主题"
    return [
        Resource(title=f"{clean} 官方入门文档", url="https://example.com/docs", source_type="doc", provider="Official docs", year=2026, est_minutes=240),
        Resource(title=f"{clean} 系统课程", url="https://example.com/course", source_type="course", provider="Open course", year=2025, est_minutes=600),
        Resource(title=f"{clean} 实战笔记", url="https://example.com/notes", source_type="blog", provider="Community", year=2024, est_minutes=120),
    ]


def run_learning_plan_offline(goal: str, days: int = 30, slot_minutes: int = 20, quiz_n: int = 3) -> dict:
    from campus.runtime.paths import runs_dir

    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join(runs_dir(), f"demo_c-offline-{ts}")
    os.makedirs(out_dir, exist_ok=True)
    candidates = offline_resources(goal)
    ranked = ranker.rank(candidates, goal)
    pick = ranked.recommendation
    plan = scheduler.build_plan(pick.resource, goal=goal, days=days, slot_minutes=slot_minutes)
    day1 = plan.days[0]
    qs = [
        QuizQuestion(q=f"{day1.topic} 的核心概念是什么？", answer="先用一句话解释概念，再列出一个例子。", explanation="用于检查是否真正理解。"),
        QuizQuestion(q="今天学习结束后应留下什么产物？", answer="一页笔记或一个可复现的小练习。", explanation="把输入变成输出。"),
        QuizQuestion(q="遇到卡点时如何记录？", answer="写下问题、尝试、下一步求助对象。", explanation="减少重复卡住。"),
    ][:max(1, quiz_n)]
    quiz = Quiz(day=1, topic=day1.topic, questions=qs)
    plan_md = plan.to_markdown()
    files = {
        "plan.md": plan_md,
        "quiz_day1.json": json.dumps(to_dict(quiz), ensure_ascii=False, indent=2),
        "research_candidates.json": json.dumps([r.__dict__ for r in candidates], ensure_ascii=False, indent=2),
    }
    for name, text in files.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(text)
    result = {
        "ok": True,
        "mode": "offline",
        "run_dir": out_dir,
        "recommendation": pick.resource.title,
        "score": pick.score,
        "days": len(plan.days),
        "quiz_questions": len(quiz.questions),
        "plan_md_head": plan_md.splitlines()[0],
    }
    with open(os.path.join(out_dir, "run_result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result
