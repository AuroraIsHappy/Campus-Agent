"""Phase 7 local product workflows.

These functions are intentionally deterministic and key-free. They give the
frontend a complete product loop while real providers remain optional adapters.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Optional

from campus.runtime.stores import ArtifactStore, RunStore, TaskStore


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:40] or "item"


def _run(domain: str, workflow: str, title: str, result: dict[str, Any],
         *, intent: str = "", status: str = "done", context: Optional[dict[str, Any]] = None,
         plan: str = "", verification: str = "") -> dict[str, Any]:
    runs = RunStore()
    artifacts = ArtifactStore(runs)
    tasks = TaskStore()
    rec = runs.create(message=title, intent=intent or workflow, domain=domain,
                      selected_workflow=workflow, context=context or {}, status="running")
    artifacts.write_text(rec.id, "Plan.md", plan or f"# Plan\n\n- task: {title}\n- workflow: {workflow}\n")
    artifacts.write_text(rec.id, "Status.md", f"# Status\n\n- status: {status}\n- updated_at: {int(time.time())}\n")
    artifacts.write_text(rec.id, "Verification.md", verification or "# Verification\n\n- local fallback completed\n- artifacts written\n")
    artifacts.write_json(rec.id, "run_result.json", result)
    manifest = artifacts.list(rec.id)
    tasks.create(title=title[:80] or workflow, body=json.dumps(result, ensure_ascii=False),
                 status=status, domain=domain, run_id=rec.id,
                 metadata={"intent": intent or workflow, "workflow": workflow})
    runs.update(rec.id, status=status, result=result, artifacts=manifest)
    result = dict(result)
    result.setdefault("ok", True)
    result["run_id"] = rec.id
    result["artifacts"] = manifest
    return result


# ---------------- Learning ----------------

def flashcards(topic: str, source_text: str = "", count: int = 8,
               mode: str = "offline", memory_snippet: str = "") -> dict[str, Any]:
    # Phase 8 Step 3: real LLM generation with offline fallback
    if mode in ("real", "auto"):
        from campus.runtime.workflow_llm import llm_generate
        llm_result = llm_generate("learning", "flashcards",
                                  {"topic": topic, "count": count}, memory_snippet=memory_snippet)
        if llm_result and llm_result.get("flashcards"):
            cards = llm_result["flashcards"][:max(1, count)]
            review_nodes = _seed_review_nodes(topic, len(cards))
            return _run("learning", "learning_flashcards", f"生成 {topic} flashcards",
                        {"ok": True, "topic": topic, "flashcards": cards,
                         "source_mode": llm_result.get("source_mode", "real_llm"),
                         "review_nodes": len(review_nodes)},
                        intent="flashcards",
                        plan=f"# Flashcards Plan (LLM)\n\n- topic: {topic}\n- count: {len(cards)}\n")
    seeds = _sentences(source_text) or [
        f"{topic} 的核心概念",
        f"{topic} 的典型例题",
        f"{topic} 的常见误区",
        f"{topic} 的复习方法",
    ]
    cards = []
    for i in range(max(1, count)):
        seed = seeds[i % len(seeds)]
        cards.append({
            "id": f"card_{i+1}",
            "front": f"{seed} 是什么？",
            "back": f"用一句话解释 {seed}，再写一个自己的例子。",
            "tags": [topic or "learning"],
            "due": _date_offset(i % 5),
        })
    review_nodes = _seed_review_nodes(topic, len(cards))
    return _run("learning", "learning_flashcards", f"生成 {topic} flashcards",
                {"ok": True, "topic": topic, "flashcards": cards, "source_mode": "local",
                 "review_nodes": len(review_nodes)},
                intent="flashcards",
                plan=f"# Flashcards Plan\n\n- topic: {topic}\n- count: {len(cards)}\n- review nodes seeded: {len(review_nodes)} (Ebbinghaus 1/3/7/16/35d)\n")


def add_deadline(title: str, due: str, course: str = "", note: str = "") -> dict[str, Any]:
    task = TaskStore().create(title=title, body=note, status="todo", domain="learning",
                              due=due, metadata={"course": course, "kind": "deadline"})
    return _run("learning", "learning_deadline", title,
                {"ok": True, "deadline": task, "source_mode": "local"},
                intent="deadline")


def list_deadlines() -> dict[str, Any]:
    tasks = [t for t in TaskStore().list()
             if t.get("domain") == "learning" and t.get("metadata", {}).get("kind") == "deadline"]
    return {"deadlines": sorted(tasks, key=lambda t: t.get("due") or "9999")}


def quiz_run(topic: str, count: int = 5, source_text: str = "",
             mode: str = "offline", memory_snippet: str = "") -> dict[str, Any]:
    if mode in ("real", "auto"):
        from campus.runtime.workflow_llm import llm_generate
        llm_result = llm_generate("learning", "quiz",
                                  {"topic": topic, "count": count}, memory_snippet=memory_snippet)
        if llm_result and llm_result.get("questions"):
            questions = llm_result["questions"][:max(1, count)]
            return _run("learning", "learning_quiz_run", f"{topic} 每日 quiz",
                        {"ok": True, "topic": topic, "questions": questions,
                         "source_mode": llm_result.get("source_mode", "real_llm")},
                        intent="quiz")
    bits = _sentences(source_text) or [topic, "今日学习内容", "关键概念", "练习反馈"]
    questions = []
    for i in range(max(1, count)):
        stem = bits[i % len(bits)]
        questions.append({
            "id": f"q{i+1}",
            "question": f"请解释：{stem}",
            "answer": f"围绕 {stem} 给出定义、例子和一个易错点。",
            "rubric": ["定义准确", "有具体例子", "能说明易错点"],
        })
    return _run("learning", "learning_quiz_run", f"{topic} 每日 quiz",
                {"ok": True, "topic": topic, "questions": questions, "source_mode": "local"},
                intent="quiz")


def quiz_grade(topic: str, answers: list[dict[str, str]]) -> dict[str, Any]:
    graded = []
    total = 0
    for a in answers:
        text = a.get("answer", "")
        score = min(100, 40 + len(text.strip()) * 3)
        total += score
        node_id = a.get("review_node_id") or ""
        correct = score >= 70
        graded.append({
            "question_id": a.get("question_id") or a.get("id", ""),
            "score": score,
            "feedback": "答案有内容基础；下一步补一个具体例子和反例。" if score < 80 else "完成度不错，继续做迁移练习。",
            "review_node_id": node_id,
            "ebbinghaus_advanced": bool(node_id),
        })
        # advance the Ebbinghaus curve for the linked review node, if any
        if node_id:
            try:
                advance_review_node(node_id, correct)
            except Exception:
                pass  # never let review-node bookkeeping fail the grade
    avg = round(total / max(1, len(graded)), 1)
    adjustment = "明天减少新内容，增加错题复盘。" if avg < 75 else "明天按原计划推进，并加入一道综合题。"
    return _run("learning", "learning_quiz_grade", f"{topic} quiz 反馈",
                {"ok": True, "topic": topic, "score": avg, "graded": graded,
                 "plan_adjustment": adjustment, "source_mode": "local"},
                intent="quiz_grade")


def learning_dashboard() -> dict[str, Any]:
    tasks = TaskStore().list()
    learning = [t for t in tasks if t.get("domain") == "learning"]
    return {
        "ok": True,
        "today_tasks": learning[:8],
        "deadlines": list_deadlines()["deadlines"],
        "due_reviews": [t for t in learning if t.get("metadata", {}).get("kind") in {"deadline", "review"}][:8],
        "progress": {"tasks": len(learning), "done": len([t for t in learning if t.get("status") == "done"])},
    }


# ---- Ebbinghaus review nodes + daily quiz (Phase 7 deepening) ----
#
# flashcards/deadlines now seed review nodes in TaskStore with an Ebbinghaus
# due date (SM-2-ish 1/3/7/16/35 day intervals). ``quiz_daily`` pulls due nodes
# and generates a quiz from them — the "daily tick can generate quiz from due
# review nodes" item from the Phase 7 plan. ``quiz_grade`` advances the curve:
# a correct answer pushes the next interval out, a weak one resets it.

_EBBINGHAUS_INTERVALS = (1, 3, 7, 16, 35)


def _ebbinghaus_due(reps_correct: int, last_ts: int) -> int:
    """Next due timestamp (epoch) given consecutive-correct count + last review."""
    idx = min(reps_correct, len(_EBBINGHAUS_INTERVALS) - 1)
    interval = _EBBINGHAUS_INTERVALS[idx]
    if reps_correct >= len(_EBBINGHAUS_INTERVALS):
        interval = int(_EBBINGHAUS_INTERVALS[-1] * (1.8 ** (reps_correct - len(_EBBINGHAUS_INTERVALS) + 1)))
    return last_ts + interval * 86400


def _seed_review_nodes(topic: str, count: int) -> list[dict[str, Any]]:
    """Create Ebbinghaus review-node tasks for a freshly generated batch of cards."""
    tasks = TaskStore()
    now = int(time.time())
    seeded = []
    for i in range(count):
        due_ts = _ebbinghaus_due(0, now)
        item = tasks.create(
            title=f"复习：{topic} card {i+1}", body="", status="todo",
            domain="learning", due=time.strftime("%Y-%m-%d", time.localtime(due_ts)),
            metadata={"kind": "review", "topic": topic, "card_index": i,
                      "reps_correct": 0, "last_ts": now, "due_ts": due_ts})
        seeded.append(item)
    return seeded


def quiz_daily(topic: str = "", count: int = 5) -> dict[str, Any]:
    """Daily-tick quiz: generate questions from Ebbinghaus-due review nodes.

    Pulls review-node tasks whose ``due_ts`` has passed (or all review nodes for
    ``topic`` if none are due yet), turns each into a quiz question, and records a
    quiz run. This is the "daily tick can generate quiz from due review nodes"
    closure from the Phase 7 plan.
    """
    now = int(time.time())
    tasks = TaskStore().list()
    review = [t for t in tasks
              if t.get("metadata", {}).get("kind") == "review"
              and t.get("domain") == "learning"
              and (not topic or t.get("metadata", {}).get("topic") == topic)]
    due = [t for t in review if (t.get("metadata", {}).get("due_ts") or 0) <= now]
    pool = due or review[:count] or []
    questions = []
    for i, t in enumerate(pool[:count] if pool else []):
        stem = t.get("title", "复习内容").replace("复习：", "")
        questions.append({
            "id": f"dq{i+1}",
            "question": f"请解释/回忆：{stem}",
            "answer": f"围绕 {stem} 给出定义、例子和一个易错点。",
            "rubric": ["定义准确", "有具体例子", "能说明易错点"],
            "review_node_id": t.get("id", ""),
        })
    if not questions:
        # No due review nodes — fall back to a fresh topic quiz so the endpoint is always useful.
        return quiz_run(topic or "今日复习", count=count)
    due_count = len(due)
    return _run("learning", "learning_quiz_daily", f"{topic or 'daily'} 每日复习 quiz",
                {"ok": True, "topic": topic or "daily", "questions": questions,
                 "source_mode": "local", "due_review_count": due_count,
                 "total_review_nodes": len(review)},
                intent="quiz_daily",
                plan=f"# Daily Quiz Plan\n\n- due review nodes: {due_count}\n- questions: {len(questions)}\n")


def advance_review_node(node_id: str, correct: bool) -> dict[str, Any]:
    """Advance (correct) or reset (wrong) the Ebbinghaus curve for a review node.

    Called by the quiz-grade path when an answer maps to a review node, so the
    next ``quiz_daily`` schedules it further out (correct) or brings it back (wrong).
    """
    tasks = TaskStore()
    all_tasks = tasks.list()
    now = int(time.time())
    for t in all_tasks:
        if t.get("id") != node_id:
            continue
        meta = dict(t.get("metadata") or {})
        if meta.get("kind") != "review":
            break
        reps = meta.get("reps_correct", 0)
        reps = reps + 1 if correct else 0
        due_ts = _ebbinghaus_due(reps, now)
        meta["reps_correct"] = reps
        meta["last_ts"] = now
        meta["due_ts"] = due_ts
        # persist back: rewrite the task list with the updated node
        t["metadata"] = meta
        t["due"] = time.strftime("%Y-%m-%d", time.localtime(due_ts))
        t["status"] = "done" if correct else "todo"
        path = tasks.path
        _write(path, all_tasks)
        return {"ok": True, "node_id": node_id, "reps_correct": reps,
                "next_due": time.strftime("%Y-%m-%d", time.localtime(due_ts)), "correct": correct}
    return {"ok": False, "error": "review node not found"}


# ---------------- Research ----------------

def research_idea(idea: str, mode: str = "offline") -> dict[str, Any]:
    from campus.research import tracker
    topic = tracker.add_topic(idea[:80] or "research idea", idea, cadence="weekly")
    digest = tracker.refresh_topic(topic["topic"]["id"], mode)
    digest["idea"] = idea
    digest["artifacts"] = []
    return _run("research", "research_idea", idea[:80] or "research idea", digest,
                intent="research_idea")


def github_trending(topic: str = "student agent", language: str = "Python",
                    mode: str = "offline", memory_snippet: str = "") -> dict[str, Any]:
    # Phase 8 Step 6: real GitHub API search (preferred over LLM for trending repos)
    if mode in ("real", "auto"):
        from campus.research.search_providers import github_search, github_available
        if github_available():
            gh_items = github_search(topic, language=language, max_results=5)
            if gh_items:
                return _run("research", "research_github_trending", f"GitHub trending: {topic}",
                            {"ok": True, "source_mode": "real_github_api", "source_error": "",
                             "summary": f"为 {topic} 从 GitHub API 检索到 {len(gh_items)} 个热门项目。",
                             "items": gh_items,
                             "questions": ["项目是否活跃？", "README 是否可复现？", "license 是否允许使用？"]},
                            intent="github_trending")
    if mode in ("real", "auto"):
        from campus.runtime.workflow_llm import llm_generate
        llm_result = llm_generate("research", "github_trending",
                                  {"topic": topic, "language": language}, memory_snippet=memory_snippet)
        if llm_result and llm_result.get("items"):
            return _run("research", "research_github_trending", f"GitHub trending: {topic}",
                        {"ok": True, "source_mode": llm_result.get("source_mode", "real_llm"),
                         "source_error": "",
                         "summary": f"为 {topic} 生成 {len(llm_result['items'])} 个推荐项目。",
                         "items": llm_result["items"],
                         "questions": ["项目是否活跃？", "README 是否可复现？", "license 是否允许使用？"]},
                        intent="github_trending")
    items = [
        {"name": f"{_slug(topic)}-starter", "url": "https://github.com/example/starter",
         "language": language, "stars": 1240, "reason": "适合作为入门工程模板"},
        {"name": f"{_slug(topic)}-rag", "url": "https://github.com/example/rag",
         "language": language, "stars": 980, "reason": "包含检索、评测和本地运行示例"},
        {"name": f"{_slug(topic)}-eval", "url": "https://github.com/example/eval",
         "language": language, "stars": 720, "reason": "适合做论文/项目复现实验"},
    ]
    return _run("research", "research_github_trending", f"GitHub trending: {topic}",
                {"ok": True, "source_mode": "fallback_offline", "source_error": "",
                 "summary": f"为 {topic} 生成 {len(items)} 个本地 fallback 项目候选。",
                 "items": items, "questions": ["项目是否活跃？", "README 是否可复现？", "license 是否允许使用？"]},
                intent="github_trending")


def format_check(title: str, target: str = "conference", manuscript: str = "") -> dict[str, Any]:
    checks = [
        {"name": "标题长度", "passed": len(title) <= 180, "detail": "标题建议控制在 180 字以内。"},
        {"name": "摘要", "passed": "摘要" in manuscript or "abstract" in manuscript.lower(), "detail": "需要摘要段。"},
        {"name": "参考文献", "passed": "参考" in manuscript or "references" in manuscript.lower(), "detail": "需要参考文献段。"},
        {"name": "图表编号", "passed": bool(re.search(r"(图|Fig\.|Table)", manuscript)), "detail": "图表需编号并在正文引用。"},
    ]
    return _run("research", "research_format_check", f"{target} 格式检查",
                {"ok": True, "source_mode": "local", "source_error": "",
                 "summary": f"{target} 格式检查完成，{sum(c['passed'] for c in checks)}/{len(checks)} 项通过。",
                 "items": checks, "questions": ["目标模板是否为最新版本？", "是否需要补充伦理/数据声明？"]},
                intent="format_check")


# ---------------- Life ----------------

def health_record(mood: str = "", sleep_hours: float = 0, exercise: str = "", note: str = "") -> dict[str, Any]:
    item = {"date": time.strftime("%Y-%m-%d"), "mood": mood, "sleep_hours": sleep_hours,
            "exercise": exercise, "note": note, "created_at": int(time.time())}
    store = RunStore()
    path = os.path.join(os.path.dirname(store.path), "health.json")
    data = _read(path, [])
    data.append(item)
    _write(path, data[-120:])
    return _run("life", "life_health", "健康 check-in",
                {"ok": True, "record": item, "records": data[-14:]}, intent="health")


def health_list() -> dict[str, Any]:
    path = os.path.join(os.path.dirname(RunStore().path), "health.json")
    return {"records": _read(path, [])}


def travel_plan(destination: str, days: int = 2, budget: int = 500, preferences: str = "",
                mode: str = "offline", memory_snippet: str = "") -> dict[str, Any]:
    if mode in ("real", "auto"):
        from campus.runtime.workflow_llm import llm_generate
        llm_result = llm_generate("life", "travel_plan",
                                  {"destination": destination, "days": days, "budget": budget},
                                  memory_snippet=memory_snippet)
        if llm_result and llm_result.get("itinerary"):
            return _run("life", "life_travel_plan", f"{destination} 旅行计划",
                        {"ok": True, "destination": destination, "days": days,
                         "preferences": preferences, "itinerary": llm_result["itinerary"],
                         "source_mode": llm_result.get("source_mode", "real_llm")}, intent="travel")
    itinerary = [
        {"day": d, "morning": f"{destination} 城市/校园路线", "afternoon": "博物馆/公园/书店",
         "evening": "轻松晚餐 + 复盘照片", "budget": round(budget / max(1, days))}
        for d in range(1, max(1, days) + 1)
    ]
    return _run("life", "life_travel_plan", f"{destination} 旅行计划",
                {"ok": True, "destination": destination, "days": days, "preferences": preferences,
                 "itinerary": itinerary, "source_mode": "local"}, intent="travel")


def campus_guide(query: str = "") -> dict[str, Any]:
    guides = [
        {"title": "报销/盖章", "steps": ["确认模板", "学院办公室初审", "校级系统提交", "保存回执"]},
        {"title": "借教室", "steps": ["确认人数和时间", "学生组织/辅导员审批", "教务系统申请", "现场确认设备"]},
        {"title": "请假", "steps": ["写明课程/时间/原因", "上传证明", "辅导员审批", "同步任课老师"]},
    ]
    hits = [g for g in guides if not query or query in g["title"]]
    return {"ok": True, "query": query, "guides": hits or guides}


# ---------------- Club ----------------

def meeting_minutes(topic: str, notes: str = "",
                    mode: str = "offline", memory_snippet: str = "") -> dict[str, Any]:
    if mode in ("real", "auto"):
        from campus.runtime.workflow_llm import llm_generate
        llm_result = llm_generate("club", "meeting_minutes",
                                  {"topic": topic, "notes": notes}, memory_snippet=memory_snippet)
        if llm_result and llm_result.get("minutes"):
            return _run("club", "club_meeting_minutes", topic,
                        {"ok": True, "topic": topic,
                         "summary": f"{topic} 会议纪要已生成（LLM）。",
                         "minutes": llm_result["minutes"],
                         "source_mode": llm_result.get("source_mode", "real_llm")},
                        intent="meeting_minutes")
    actions = [s for s in _sentences(notes)[:5]] or ["确认负责人", "下次会议前交付初稿"]
    result = {"ok": True, "topic": topic, "summary": f"{topic} 会议纪要已生成。",
              "minutes": {"decisions": actions[:3], "todo": actions, "next_meeting": "下周同一时间确认进展"}}
    return _run("club", "club_meeting_minutes", topic, result, intent="meeting_minutes")


def recruiting_copy(org: str, audience: str = "大一新生", tone: str = "热情",
                    mode: str = "offline", memory_snippet: str = "") -> dict[str, Any]:
    if mode in ("real", "auto"):
        from campus.runtime.workflow_llm import llm_generate
        llm_result = llm_generate("club", "recruiting_copy",
                                  {"org": org, "audience": audience, "tone": tone},
                                  memory_snippet=memory_snippet)
        if llm_result and llm_result.get("copy"):
            copy = llm_result["copy"]
            copy.setdefault("tone", tone)
            return _run("club", "club_recruiting_copy", f"{org} 招新文案",
                        {"ok": True, "copy": copy,
                         "source_mode": llm_result.get("source_mode", "real_llm")},
                        intent="recruiting_copy")
    copy = {
        "headline": f"加入{org}，把你的想法做成真实项目",
        "body": f"面向{audience}，我们准备了低门槛培训、项目搭档和展示机会。欢迎喜欢行动的人来聊聊。",
        "poster_points": ["低门槛", "有 mentor", "能产出作品", "氛围友好"],
        "tone": tone,
    }
    return _run("club", "club_recruiting_copy", f"{org} 招新文案",
                {"ok": True, "copy": copy}, intent="recruiting_copy")


def email_draft(purpose: str, recipient: str = "", context: str = "",
                mode: str = "offline", memory_snippet: str = "") -> dict[str, Any]:
    if mode in ("real", "auto"):
        from campus.runtime.workflow_llm import llm_generate
        llm_result = llm_generate("club", "email_draft",
                                  {"purpose": purpose, "recipient": recipient, "context": context},
                                  memory_snippet=memory_snippet)
        if llm_result and llm_result.get("email"):
            return _run("club", "club_email_draft", purpose,
                        {"ok": True, "email": llm_result["email"], "recipient": recipient,
                         "source_mode": llm_result.get("source_mode", "real_llm")},
                        intent="email_draft")
    text = f"{recipient or '老师/同学'}您好：\n\n我是校园项目负责人，想就“{purpose}”与您沟通。{context}\n\n如果方便，期待约一个 15 分钟的时间确认细节。谢谢！"
    return _run("club", "club_email_draft", purpose,
                {"ok": True, "email": text, "recipient": recipient}, intent="email_draft")


# ---------------- Career ----------------

def job_search(query: str, city: str = "", mode: str = "offline") -> dict[str, Any]:
    jobs = [
        {"id": f"job_{i}", "title": f"{query} 实习 {i}", "company": c, "city": city or "远程",
         "url": f"https://jobs.example.com/{_slug(query)}-{i}", "fit": 92 - i * 6,
         "reason": "技能要求与学生项目经历匹配，适合投递练习。"}
        for i, c in enumerate(["校园智能科技", "开源教育实验室", "未来数据中心"], 1)
    ]
    return _run("career", "career_jobs_search", f"搜索实习：{query}",
                {"ok": True, "source_mode": "fallback_offline", "source_error": "",
                 "jobs": jobs, "query": query, "city": city, "mode": mode}, intent="job_search")


def save_job(job: dict[str, Any]) -> dict[str, Any]:
    path = os.path.join(os.path.dirname(RunStore().path), "saved_jobs.json")
    jobs = _read(path, [])
    if not job.get("id"):
        job["id"] = f"job_{int(time.time())}"
    jobs = [j for j in jobs if j.get("id") != job.get("id")] + [job]
    _write(path, jobs)
    return {"ok": True, "job": job, "jobs": jobs}


def list_jobs() -> dict[str, Any]:
    path = os.path.join(os.path.dirname(RunStore().path), "saved_jobs.json")
    return {"jobs": _read(path, [])}


def interview_plan(role: str, days: int = 7, background: str = "",
                   mode: str = "offline", memory_snippet: str = "") -> dict[str, Any]:
    if mode in ("real", "auto"):
        from campus.runtime.workflow_llm import llm_generate
        llm_result = llm_generate("career", "interview_plan",
                                  {"role": role, "days": days, "background": background},
                                  memory_snippet=memory_snippet)
        if llm_result and (llm_result.get("plan") or llm_result.get("questions")):
            return _run("career", "career_interview_plan", f"{role} 面试计划",
                        {"ok": True, "role": role, "days": days, "background": background,
                         "plan": llm_result.get("plan", []),
                         "questions": llm_result.get("questions", []),
                         "source_mode": llm_result.get("source_mode", "real_llm")}, intent="interview_plan")
    plan = [
        {"day": d, "focus": focus, "task": f"准备 {role}：{focus}", "minutes": 45}
        for d, focus in enumerate(["岗位拆解", "项目故事", "基础知识", "算法/案例", "模拟问答", "复盘补缺", "最终演练"][:max(1, days)], 1)
    ]
    questions = [
        f"请介绍一个最能体现你适合 {role} 的项目。",
        "遇到冲突或卡点时你如何推进？",
        "你希望这段实习带来什么成长？",
    ]
    return _run("career", "career_interview_plan", f"{role} 面试计划",
                {"ok": True, "role": role, "days": days, "background": background,
                 "plan": plan, "questions": questions}, intent="interview_plan")


def interview_practice(role: str, question: str = "", answer: str = "",
                       background: str = "") -> dict[str, Any]:
    """Practice one interview question: score the answer + give improvement cues.

    The "interview question practice" item from the Phase 7 plan. Produces a
    scored practice record (rubric + model answer outline + follow-up) and writes
    it as a run artifact so the user can review their practice history.
    """
    q = question or f"请介绍一个最能体现你适合 {role} 的项目。"
    rubric = [
        "结构清晰(STAR: 情境-任务-行动-结果)",
        "有量化结果或具体产出",
        "体现个人贡献而非团队笼统描述",
        "与岗位 {role} 的能力要求相关",
    ]
    a_len = len((answer or "").strip())
    score = min(100, 35 + a_len // 3)
    cues = []
    if a_len < 60:
        cues.append("回答偏短,尝试展开具体行动和结果。")
    if "我" not in (answer or "") and a_len > 0:
        cues.append("多用'我做了…'明确个人贡献。")
    if not any(w in (answer or "") for w in ("结果", "完成", "实现", "提升", "数据")):
        cues.append("补一个量化结果(数字/时间/规模)。")
    model_outline = [
        f"情境: {role} 相关的一个真实场景背景",
        "任务: 你负责解决的具体问题",
        "行动: 你采取的 2-3 个关键步骤(技术/沟通/取舍)",
        "结果: 可量化的产出 + 你的收获",
    ]
    follow_ups = [
        f"如果时间减半,你会优先砍掉哪个步骤?",
        "这个项目里你最大的技术/沟通挑战是什么?",
    ]
    return _run("career", "career_interview_practice", f"{role} 面试练习",
                {"ok": True, "role": role, "question": q, "answer": answer,
                 "score": score, "rubric": [r.format(role=role) if "{" in r else r for r in rubric],
                 "improvement_cues": cues or ["回答结构完整,可继续精简表达。"],
                 "model_answer_outline": model_outline,
                 "follow_ups": follow_ups, "background": background,
                 "source_mode": "local"}, intent="interview_practice",
                plan=f"# Interview Practice\n\n- role: {role}\n- question: {q}\n- score: {score}\n")


def interview_reflect(role: str, reflection: str, practice_run_id: str = "",
                      tags: str = "") -> dict[str, Any]:
    """Write a reflection note after interview practice (Phase 7 plan item).

    Stores the user's free-text reflection as an artifact + a knowledge memory
    record so future interview prep can recall what they learned.
    """
    note = {
        "role": role, "reflection": reflection, "practice_run_id": practice_run_id,
        "tags": [t.strip() for t in (tags or "").split(",") if t.strip()],
        "created_at": int(time.time()),
    }
    # also persist to a reflection log so history is queryable
    path = os.path.join(os.path.dirname(RunStore().path), "interview_reflections.json")
    reflections = _read(path, [])
    reflections.append(note)
    _write(path, reflections[-200:])
    return _run("career", "career_interview_reflect", f"{role} 面试反思",
                {"ok": True, "reflection": note, "reflections_total": len(reflections)},
                intent="interview_reflect")


def export_status() -> dict[str, Any]:
    """Report which office-document export libraries are locally available.

    The "expose document export status for docx/pptx/xlsx" item from the Phase 7
    plan. Checks the optional document-processing deps (python-docx, python-pptx,
    openpyxl) and reports per-format readiness so the frontend can show what
    export targets are available without trying and failing.
    """
    formats = {}
    for fmt, mod, label in [
        ("docx", "docx", "python-docx"),
        ("pptx", "pptx", "python-pptx"),
        ("xlsx", "openpyxl", "openpyxl"),
    ]:
        try:
            __import__(mod)
            formats[fmt] = {"available": True, "library": label}
        except ImportError:
            formats[fmt] = {"available": False, "library": label,
                            "hint": f"pip install {label}"}
    # optional: PDF via reportlab (not in requirements yet)
    try:
        __import__("reportlab")
        formats["pdf"] = {"available": True, "library": "reportlab"}
    except ImportError:
        formats["pdf"] = {"available": False, "library": "reportlab",
                          "hint": "pip install reportlab (optional)"}
    return {"ok": True, "formats": formats,
            "any_available": any(f["available"] for f in formats.values())}


def _sentences(text: str) -> list[str]:
    return [s.strip(" \n\t。.!?？") for s in re.split(r"[。.!?？\n]+", text or "") if s.strip()][:20]


def _date_offset(days: int) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(time.time() + days * 86400))


def _read(path: str, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
