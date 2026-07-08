"""Orchestrator: full Demo C chain - goal -> research -> rank -> plan -> day1 quiz -> memory."""
from __future__ import annotations
import argparse, json, os, re, datetime as dt
from . import researcher, ranker, scheduler, quiz, memory
from .types import to_dict
from campus.runtime.paths import runs_dir

RUNS = runs_dir()
NL = chr(10)


def _slug(s):
    return (re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:40]) or "goal"


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def run_learning_plan(goal, days=30, slot_minutes=20, quiz_n=3, sync_calendar=""):
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join(RUNS, ts)
    os.makedirs(out_dir, exist_ok=True)

    candidates = researcher.search_resources(goal, top_k=6)
    ranked = ranker.rank(candidates, goal)
    if not ranked.recommendation:
        _write(os.path.join(out_dir, "run_result.json"),
               json.dumps({"ok": False, "error": "no candidates", "candidates": len(candidates)}, ensure_ascii=False, indent=2))
        return {"ok": False, "error": "no candidates found", "run_dir": out_dir}

    pick = ranked.recommendation
    res = pick.resource
    topics = scheduler.suggest_topics(res, goal, days=days)
    plan = scheduler.build_plan(res, goal=goal, days=days, slot_minutes=slot_minutes, topics=topics)
    day1 = plan.days[0] if plan.days else None
    day1_quiz = quiz.generate_quiz(day1.topic, resource=res.title, n=quiz_n) if day1 else None

    memory.set_goal(goal)
    memory.remember({"learning": goal, "resource": res.title, "run": ts})
    if day1:
        memory.log_progress(_slug(goal), 1, "planned", "day1 quiz generated")

    # Phase 9: calendar sync (GOAL.md 同步飞书&本地日历)
    calendar_sync = {"ok": False, "skipped": True}
    if sync_calendar and plan.days:
        try:
            from campus.life.plan_calendar import sync_demo_c_plan
            local = sync_calendar in ("local", "both")
            feishu = sync_calendar in ("feishu", "both")
            calendar_sync = sync_demo_c_plan(
                plan, slot_time="20:00", local=local, feishu=feishu)
        except Exception as e:
            calendar_sync = {"ok": False, "error": str(e)[:200]}

    plan_md = plan.to_markdown()
    _write(os.path.join(out_dir, "plan.md"), plan_md)
    _write(os.path.join(out_dir, "quiz_day1.json"),
           json.dumps(to_dict(day1_quiz), ensure_ascii=False, indent=2))
    _write(os.path.join(out_dir, "research_candidates.json"),
           json.dumps([r.__dict__ for r in candidates], ensure_ascii=False, indent=2))
    _write(os.path.join(out_dir, "progress.json"),
           json.dumps({"goal": goal, "days_total": len(plan.days), "day1": "quiz_ready",
                       "resource": res.title}, ensure_ascii=False, indent=2))
    _write(os.path.join(out_dir, "run_result.json"),
           json.dumps({"ok": True, "goal": goal, "ts": ts, "run_dir": out_dir,
                       "recommendation": {"title": res.title, "url": res.url,
                                          "score": pick.score, "reasons": pick.reasons},
                       "days": len(plan.days),
                       "quiz_questions": len(day1_quiz.questions) if day1_quiz else 0,
                       "calendar_sync": calendar_sync},
                      ensure_ascii=False, indent=2))

    return {"ok": True, "run_dir": out_dir,
            "recommendation": res.title, "score": pick.score,
            "days": len(plan.days),
            "quiz_questions": len(day1_quiz.questions) if day1_quiz else 0,
            "plan_md_head": plan_md.split(NL)[0],
            "calendar_sync": calendar_sync}


def _main():
    ap = argparse.ArgumentParser(description="Demo C: goal -> 30-day plan + day1 quiz.")
    ap.add_argument("goal")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--minutes", type=int, default=20)
    ap.add_argument("--quiz-n", type=int, default=3)
    args = ap.parse_args()
    print(json.dumps(run_learning_plan(args.goal, days=args.days,
                                       slot_minutes=args.minutes, quiz_n=args.quiz_n),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()
