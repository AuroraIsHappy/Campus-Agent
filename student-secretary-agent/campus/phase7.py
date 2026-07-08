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

def flashcards(topic: str, source_text: str = "", count: int = 8) -> dict[str, Any]:
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
    return _run("learning", "learning_flashcards", f"生成 {topic} flashcards",
                {"ok": True, "topic": topic, "flashcards": cards, "source_mode": "local"},
                intent="flashcards",
                plan=f"# Flashcards Plan\n\n- topic: {topic}\n- count: {len(cards)}\n")


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


def quiz_run(topic: str, count: int = 5, source_text: str = "") -> dict[str, Any]:
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
        graded.append({
            "question_id": a.get("question_id") or a.get("id", ""),
            "score": score,
            "feedback": "答案有内容基础；下一步补一个具体例子和反例。" if score < 80 else "完成度不错，继续做迁移练习。",
        })
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


# ---------------- Research ----------------

def research_idea(idea: str, mode: str = "offline") -> dict[str, Any]:
    from campus.research import tracker
    topic = tracker.add_topic(idea[:80] or "research idea", idea, cadence="weekly")
    digest = tracker.refresh_topic(topic["topic"]["id"], mode)
    digest["idea"] = idea
    digest["artifacts"] = []
    return _run("research", "research_idea", idea[:80] or "research idea", digest,
                intent="research_idea")


def github_trending(topic: str = "student agent", language: str = "Python") -> dict[str, Any]:
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


def travel_plan(destination: str, days: int = 2, budget: int = 500, preferences: str = "") -> dict[str, Any]:
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

def meeting_minutes(topic: str, notes: str = "") -> dict[str, Any]:
    actions = [s for s in _sentences(notes)[:5]] or ["确认负责人", "下次会议前交付初稿"]
    result = {"ok": True, "topic": topic, "summary": f"{topic} 会议纪要已生成。",
              "minutes": {"decisions": actions[:3], "todo": actions, "next_meeting": "下周同一时间确认进展"}}
    return _run("club", "club_meeting_minutes", topic, result, intent="meeting_minutes")


def recruiting_copy(org: str, audience: str = "大一新生", tone: str = "热情") -> dict[str, Any]:
    copy = {
        "headline": f"加入{org}，把你的想法做成真实项目",
        "body": f"面向{audience}，我们准备了低门槛培训、项目搭档和展示机会。欢迎喜欢行动的人来聊聊。",
        "poster_points": ["低门槛", "有 mentor", "能产出作品", "氛围友好"],
        "tone": tone,
    }
    return _run("club", "club_recruiting_copy", f"{org} 招新文案",
                {"ok": True, "copy": copy}, intent="recruiting_copy")


def email_draft(purpose: str, recipient: str = "", context: str = "") -> dict[str, Any]:
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


def interview_plan(role: str, days: int = 7, background: str = "") -> dict[str, Any]:
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
