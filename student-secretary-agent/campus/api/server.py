"""FastAPI app for the Campus frontend (Phase 5).

``create_app(backends=...)`` builds the app; every route delegates to a backend
callable stored in ``app.state.backends``. Default backends call the real campus
libraries (demo_b pipeline, onboarding); tests inject fakes so the TestClient
suite is deterministic (no Hermes / no network / no real model).

Run for real:  ``uvicorn campus.api.server:app`` (after ``create_app()``).
"""
from __future__ import annotations
import os
import json
from dataclasses import dataclass
from typing import Any, Callable, Optional

from fastapi import FastAPI

from campus.api.types import (
    AgentRunRequest, AgentChatRequest, DemoARequest, DemoBRequest, DemoCRequest, MemoryQuery, OnboardingRequest, PushRequest,
    EventRequest, AnniversaryRequest, LogQuery, ResearchTopicRequest,
    ResearchRefreshRequest, NotionSyncRequest, ZoteroSyncRequest, ZoteroSearchRequest,
    FlashcardsRequest, DeadlineRequest, QuizRunRequest, QuizGradeRequest,
    ResearchIdeaRequest, GithubTrendingRequest, FormatCheckRequest,
    HealthRequest, TravelPlanRequest, ClubMinutesRequest, RecruitingCopyRequest,
    EmailDraftRequest, JobSearchRequest, JobSaveRequest, InterviewPlanRequest,
    InterviewPracticeRequest, InterviewReflectRequest,
    CorrectionRequest, AgentNameRequest,
)

__all__ = ["Backends", "create_app", "app", "start_scheduler", "stop_scheduler"]


@dataclass
class Backends:
    """Injectable service callables. Any left None uses a sane default."""
    demo_a_run: Callable[[DemoARequest], dict]
    demo_b_run: Callable[[DemoBRequest], dict]
    demo_c_run: Callable[[DemoCRequest], dict]
    demo_status: Callable[[], dict]
    memory_recall: Callable[[str, int], list]
    onboarding_run: Callable[[dict], dict]
    list_tasks: Callable[[], list]
    push_send: Callable[[str, Optional[str], str], dict]
    research_add_topic: Optional[Callable[[ResearchTopicRequest], dict]] = None
    research_list_topics: Optional[Callable[[], dict]] = None
    research_refresh: Optional[Callable[[str, ResearchRefreshRequest], dict]] = None
    research_runs: Optional[Callable[[], dict]] = None
    notion_sync: Optional[Callable[[NotionSyncRequest], dict]] = None
    notes_status: Optional[Callable[[], dict]] = None
    # life (Phase 6) — Optional so phase-5 callers that omit them still work
    calendar_add: Optional[Callable[[EventRequest], dict]] = None
    calendar_list: Optional[Callable[[Optional[str], Optional[str]], dict]] = None
    calendar_delete: Optional[Callable[[str], dict]] = None
    anniv_add: Optional[Callable[[AnniversaryRequest], dict]] = None
    anniv_list: Optional[Callable[[], dict]] = None
    daily_log_get: Optional[Callable[[Optional[str], int], dict]] = None
    daily_log_run: Optional[Callable[[], dict]] = None
    agent_run: Optional[Callable[[AgentRunRequest], dict]] = None
    agent_list_runs: Optional[Callable[[], dict]] = None
    agent_get_run: Optional[Callable[[str], dict]] = None
    settings_status: Optional[Callable[[], dict]] = None


# ---- default backends (real campus libs; deterministic where possible) ----

def _default_demo_a(req: DemoARequest) -> dict:
    from campus.demo_a.types import Brief, SampleSpec
    from campus.demo_a import pipeline as _p
    from campus.runtime.llm_config import require_real_llm, resolve_mode

    real, status = require_real_llm(req.mode)
    if resolve_mode(req.mode) == "real" and not status.get("ok"):
        return {"ok": False, "mode": "real", "error": status["error"], "real_llm": status}

    sample = SampleSpec(raw=req.sample_text or "# 样例\n## 背景\n## 预算\n## 时间表\n## 安全预案")
    brief = Brief(topic=req.topic, region=req.region, window=req.window)
    turn = None
    opener = None
    if not real:
        from campus.demo_a.offline import make_offline_turn
        run_dir = _p.new_run_dir()
        opener = lambda url, timeout=5: 200
        result = _p.run_demo_a(sample, brief, turn_factory=make_offline_turn,
                               run_dir=run_dir, url_opener=opener, sup_max_rounds=1)
    else:
        try:
            result = _p.run_demo_a(sample, brief)
        except Exception as e:
            return {"ok": False, "mode": "real", "error": str(e), "real_llm": status}
    data = {
        "ok": result.ok,
        "mode": "real" if real else "offline",
        "run_dir": result.run_dir,
        "final_status": result.final_status,
        "outreach_count": result.outreach_count,
        "email_segments": result.email_segments,
        "checks": [getattr(c, "__dict__", c) for c in result.checks],
        "debates": result.debates,
        "artifacts": result.artifacts,
        "error": result.error,
        "real_llm": status,
    }
    return data

def _default_demo_b(req: DemoBRequest) -> dict:
    from campus.demo_b import pipeline as _p
    from campus.demo_b import path_resolver as _pr
    import os

    path = req.path
    # Phase 9: fuzzy path resolution (GOAL.md 模糊路径 + 自动确认)
    # If the path doesn't point to a real file/dir, treat it as a fuzzy query
    # and resolve candidates from ~/Desktop, ~/Documents, etc.
    needs_clarify = False
    clarify_options: list = []
    if path and not os.path.exists(os.path.expanduser(path)):
        resolver_fn = None
        try:
            resolver_fn = _pr.make_llm_resolver_fn()
        except Exception:
            pass
        resolution = _pr.resolve_lecture_path(path, resolver_fn=resolver_fn)
        if resolution["resolved"]:
            path = resolution["resolved"]
        elif resolution["needs_clarify"]:
            return {"ok": False, "needs_clarify": True,
                    "clarify_options": resolution["clarify_options"],
                    "candidates": resolution["candidates"],
                    "message": f"在 {path} 附近找到多个可能的讲义文件，请确认是哪一个。"}
        else:
            return {"ok": False, "needs_clarify": False,
                    "error": f"未找到匹配 '{path}' 的讲义文件。请提供完整路径。"}

    r = _p.run_demo_b(path, req.exam_date, free_minutes=req.free_minutes,
                      start_date=req.start_date, topic=req.topic,
                      export_notion=bool(getattr(req, "export_notion", False)),
                      sync_calendar=getattr(req, "sync_calendar", ""))
    d = _result_dict(r)
    d["topic"] = req.topic or ""
    return d


def _default_demo_c(req: DemoCRequest) -> dict:
    from campus.runtime.llm_config import require_real_llm, resolve_mode
    real, status = require_real_llm(req.mode)
    if resolve_mode(req.mode) == "real" and not status.get("ok"):
        return {"ok": False, "mode": "real", "error": status["error"], "real_llm": status}
    if real:
        try:
            from campus.demo_c.orchestrator import run_learning_plan
            result = run_learning_plan(req.goal, days=req.days, slot_minutes=req.minutes, quiz_n=req.quiz_n)
            result["mode"] = "real"
        except Exception as e:
            return {"ok": False, "mode": "real", "error": str(e), "real_llm": status}
    else:
        from campus.demo_c.offline import run_learning_plan_offline
        result = run_learning_plan_offline(req.goal, days=req.days, slot_minutes=req.minutes, quiz_n=req.quiz_n)
    result["real_llm"] = status
    return result


def _default_demo_status() -> dict:
    from campus.skills.registry import audit
    return audit()


def _result_dict(r) -> dict:
    return {
        "ok": r.ok, "run_dir": r.run_dir, "final_status": r.final_status,
        "extraction_rate": r.extraction_rate, "kg_nodes": r.kg_nodes,
        "resource_count": r.resource_count, "plan_days": r.plan_days,
    }


def _default_memory_recall(query: str, k: int) -> list:
    from campus.memory.json_store import JsonFileStore
    return [
        {"key": r.record.key, "score": r.score, "snippet": r.snippet,
         "layer": r.record.layer, "metadata": r.record.metadata}
        for r in JsonFileStore().recall(query, k=k)
    ]


def _default_onboarding(answers: dict) -> dict:
    # Phase 8 Step 1: wired to the real OnboardingWizard. The frontend sends a
    # dict of answers; the wizard normalizes providers/persona + recommends skills.
    # If answers are sparse, we still return what we have + the question list so
    # the frontend can drive a multi-step form.
    from campus.meta_agent.onboarding import OnboardingWizard, recommend_skills

    questions = [{"key": k, "question": q} for k, q in OnboardingWizard.QUESTIONS]

    # If the caller passed a full answer set, run the wizard to produce a profile.
    required = {"identity", "major", "persona"}
    if required.issubset({k for k, v in (answers or {}).items() if v}):
        def _ask(q: str) -> str:
            # map question → answer by key (QUESTIONS order is stable)
            for k, question in OnboardingWizard.QUESTIONS:
                if question == q:
                    return str((answers or {}).get(k, ""))
            return ""
        try:
            profile = OnboardingWizard(ask=_ask).run()
            skills = recommend_skills(profile)
            # persist the profile to memory so future sessions recall it
            try:
                from campus.memory.json_store import JsonFileStore
                from campus.memory.types import PREFERENCES
                store = JsonFileStore()
                store.remember(layer=PREFERENCES, key="onboarding_profile",
                               content=str(profile.__dict__),
                               metadata={"identity": profile.identity,
                                         "major": profile.major,
                                         "persona": profile.persona},
                               pinned=True)
            except Exception:
                pass
            return {"ok": True, "profile": profile.__dict__,
                    "recommended_skills": skills, "questions": questions}
        except Exception as e:
            return {"ok": False, "error": str(e),
                    "profile": {"identity": answers.get("identity", ""),
                                "major": answers.get("major", ""),
                                "persona": answers.get("persona", "default")},
                    "questions": questions}

    # partial answers → return questions so the frontend can continue the form
    return {"ok": True,
            "profile": {"identity": answers.get("identity", ""),
                        "major": answers.get("major", ""),
                        "persona": answers.get("persona", "default")},
            "questions": questions}


def _default_tasks() -> list:
    from campus.runtime.stores import TaskStore
    return TaskStore().list()


def _default_push(channel: str, target: Optional[str], message: str) -> dict:
    try:
        from campus.mobile.cli import push as _push  # real if campus.mobile exists
        receipt = _push(channel, target, message)
        return {"ok": receipt.ok, "channel": receipt.channel,
                "target": receipt.target, "error": receipt.error}
    except Exception as e:
        return {"ok": False, "channel": channel, "target": target, "error": str(e)}


def _default_research_add_topic(req: ResearchTopicRequest) -> dict:
    from campus.research import tracker
    return tracker.add_topic(req.title, req.query, req.keywords, req.cadence)


def _default_research_list_topics() -> dict:
    from campus.research import tracker
    return {"topics": tracker.list_topics()}


def _default_research_refresh(topic_id: str, req: ResearchRefreshRequest) -> dict:
    from campus.research import tracker
    return tracker.refresh_topic(topic_id, req.mode)


def _default_research_runs() -> dict:
    from campus.research import tracker
    return {"runs": tracker.list_runs()}


def _default_notion_sync(req: NotionSyncRequest) -> dict:
    from campus.notes import notion
    return notion.sync_digest(req.digest, req.mode)


def _default_notes_status() -> dict:
    from campus.notes import notion
    return notion.status()


def _classify_agent_message(message: str) -> tuple[str, str, str]:
    m = (message or "").lower()
    if any(k in m for k in ("学习", "复习", "quiz", "flashcard", "课程", "lecture", "计划", "learn")):
        return "learning_plan", "learning", "demo_c_learning_plan"
    if any(k in m for k in ("科研", "论文", "paper", "research", "github", "文献")):
        return "research_idea", "research", "research_topic_refresh"
    if any(k in m for k in ("社团", "实践", "活动", "招新", "会议", "club")):
        return "club_practice", "club", "demo_a_social_practice"
    if any(k in m for k in ("健康", "旅行", "日程", "生日", "生活", "办事")):
        return "life_task", "life", "local_life_secretary"
    if any(k in m for k in ("实习", "面试", "简历", "career", "job")):
        return "career_plan", "career", "local_career_secretary"
    return "general_secretary", "general", "local_secretary"


def _default_agent_run(req: AgentRunRequest) -> dict:
    from campus.api.types import DemoARequest, DemoCRequest, ResearchRefreshRequest, ResearchTopicRequest
    from campus import phase7
    from campus.runtime.llm_config import require_real_llm, resolve_mode
    from campus.runtime.stores import ArtifactStore, RunStore, TaskStore

    intent, domain, workflow = _classify_agent_message(req.message)
    runs = RunStore()
    artifacts = ArtifactStore(runs)
    tasks = TaskStore()
    rec = runs.create(message=req.message, intent=intent, domain=domain,
                      selected_workflow=workflow, context=req.context)
    artifacts.write_text(rec.id, "Plan.md", f"# Plan\n\n- request: {req.message}\n- workflow: {workflow}\n")
    status = "done"
    error = ""
    result: dict[str, Any] = {"ok": True}

    # Phase 8 Step 1: real/auto + long-horizon tasks go through the MetaAgent →
    # Odyssey multi-agent DAG (Planner↔Critic / Writer↔Reviewer adversarial
    # debate) instead of the deterministic phase7 shortcut. Offline mode keeps
    # the existing deterministic routing for backward compatibility + hermetic tests.
    resolved = resolve_mode(req.mode)
    use_meta = False
    if resolved != "offline":
        real, llm_status = require_real_llm(req.mode)
        if real:
            # long-horizon cue? delegate to MetaRunner for full multi-agent DAG.
            from campus.meta_agent.meta_agent import LONG_KEYWORDS
            is_long = len(req.message) > 20 or any(k in req.message for k in LONG_KEYWORDS)
            if is_long:
                use_meta = True

    try:
        if use_meta:
            from campus.meta_agent.runner import MetaRunner
            mr = MetaRunner()
            mem = _try_recall_memory(req.message, k=3)
            r = mr.run(req.message, mode=req.mode, domain=domain,
                       context=req.context, memory_snippet=mem)
            if r.ok:
                # MetaRunner already persisted its own run record + artifacts;
                # adopt its run_id and skip the manual artifact import below.
                status = r.final_status or "done"
                result = {"ok": True, "kind": r.kind, "summary": r.summary,
                          "debates": r.debates, "dag": r.dag, "mode": req.mode,
                          "multiagent": True, "artifacts": r.artifacts}
                # mark the pre-created record as superseded by the meta run
                runs.update(rec.id, status="superseded",
                            result={"meta_run_id": r.run_id, "multiagent": True})
                rec = runs.get(r.run_id) or rec  # adopt the meta run record
            else:
                status = "failed"
                error = r.error
                result = {"ok": False, "error": error, "multiagent": True}
        elif domain == "learning":
            days = int(req.context.get("days", 30)) if isinstance(req.context, dict) else 30
            result = _default_demo_c(DemoCRequest(goal=req.message, days=days, mode=req.mode))
        elif domain == "club":
            result = _default_demo_a(DemoARequest(topic=req.message[:80] or "校园活动", mode=req.mode))
        elif domain == "research":
            topic = _default_research_add_topic(ResearchTopicRequest(title=req.message[:80] or "research idea", query=req.message))
            result = _default_research_refresh(topic["topic"]["id"], ResearchRefreshRequest(mode=req.mode))
        elif domain == "life":
            result = phase7.travel_plan(req.message[:40] or "周末", days=1, preferences=req.message)
        elif domain == "career":
            result = phase7.interview_plan(req.message[:40] or "实习岗位", days=7, background=req.message)
        else:
            result = phase7.email_draft(req.message[:80] or "沟通事项", context=req.message)
        if not result.get("ok", False):
            status = "failed"
            error = result.get("error", "")
    except Exception as e:
        status = "failed"
        error = str(e)
        result = {"ok": False, "error": error}
    # MetaRunner already persisted its own run record + artifacts; skip the
    # manual artifact import for the multi-agent path (artifacts are already dicts).
    if use_meta and result.get("multiagent"):
        imported = result.get("artifacts", [])
    else:
        imported = artifacts.import_paths(rec.id, result.get("artifacts", []))
    if result.get("run_dir"):
        imported.append(artifacts.write_text(rec.id, "SourceRun.txt", str(result["run_dir"]), "reference"))
    artifacts.write_text(rec.id, "Status.md", f"# Status\n\n- status: {status}\n- error: {error}\n- multiagent: {bool(result.get('multiagent'))}\n")
    artifacts.write_text(rec.id, "Verification.md", f"# Verification\n\n- local fallback safe: yes\n- result ok: {bool(result.get('ok'))}\n- multiagent: {bool(result.get('multiagent'))}\n")
    artifacts.write_json(rec.id, "run_result.json", result)
    manifest = artifacts.list(rec.id)
    tasks.create(title=req.message[:80] or intent, body=req.message, status=status,
                 domain=domain, run_id=rec.id, metadata={"intent": intent, "workflow": workflow})
    runs.update(rec.id, status=status, error=error, result=result, artifacts=manifest)
    return {
        "ok": status != "failed",
        "run_id": rec.id,
        "intent": intent,
        "domain": domain,
        "selected_workflow": workflow,
        "status": status,
        "artifacts": manifest,
        "error": error,
        "multiagent": bool(result.get("multiagent")),
    }


def _try_recall_memory(query: str, k: int = 3) -> str:
    """Best-effort layered memory recall for context injection. Never raises.

    Phase 8 Step 2: uses ``recall_layered`` (tiered per-layer rules + RRF fusion +
    token-budget packing) instead of the flat ``recall()`` scan. Returns a formatted
    snippet ready to paste into an LLM prompt.
    """
    try:
        from campus.memory.json_store import JsonFileStore
        from campus.memory.recall_strategy import recall_layered
        store = JsonFileStore()
        packed = recall_layered(store, query, token_budget=1500)
        return packed.snippet
    except Exception:
        return ""


def _default_agent_list_runs() -> dict:
    from campus.runtime.stores import RunStore
    return {"runs": RunStore().list()}


def _default_agent_get_run(run_id: str) -> dict:
    from campus.runtime.stores import ArtifactStore, RunStore
    rec = RunStore().get(run_id)
    if rec is None:
        return {"ok": False, "error": "run not found"}
    data = rec.__dict__
    data["ok"] = True
    data["artifacts"] = ArtifactStore().list(run_id)
    return data


def _default_agent_chat(req: AgentChatRequest) -> dict:
    """Chat-first endpoint (Phase 9 — GOAL.md 飞书式聊天).

    Runs the agent (reusing ``_default_agent_run``), then composes a persona-
    styled natural-language reply from the structured result + conversation
    history + recalled memory. Persists the turn to ``ConversationStore``.

    Supports clarification flows: if the agent result carries ``needs_clarify``
    + ``clarify_options`` (e.g. fuzzy lecture path), the reply asks the user to
    confirm rather than silently proceeding.
    """
    from campus.conversation.store import ConversationStore
    from campus.conversation.reply import compose_reply, resolve_persona_name

    store = ConversationStore()
    persona_name = resolve_persona_name(req.persona)
    history = store.history(req.conversation_id) if req.conversation_id else []
    memory_snippet = _try_recall_memory(req.message, k=3)

    # Pass context (e.g. confirmed_path, sync_calendar) through to the agent run.
    run_req = AgentRunRequest(message=req.message, mode=req.mode,
                              context=req.context or {})

    # Run the agent. Inject clarification context: if the user is confirming a
    # prior ambiguous choice, the context carries the resolved path so the run
    # proceeds without re-asking.
    result = _default_agent_run(run_req)

    # Compose the persona-styled reply from the structured result.
    composed = compose_reply(
        message=req.message, run_result=result,
        persona_name=persona_name, history=history,
        memory_snippet=memory_snippet,
    )

    # Persist user + assistant turns.
    now_ts = __import__("time").time()
    added = store.append(conversation_id=req.conversation_id, role="user",
                         content=req.message, now=int(now_ts))
    conv_id = added["conversation_id"]
    store.append(conversation_id=conv_id, role="assistant",
                 content=composed["reply"], run_id=result.get("run_id", ""),
                 persona=persona_name, now=int(now_ts))

    return {
        "ok": result.get("ok", False),
        "reply": composed["reply"],
        "run_id": result.get("run_id", ""),
        "status": result.get("status", ""),
        "domain": result.get("domain", ""),
        "intent": result.get("intent", ""),
        "artifacts": result.get("artifacts", []),
        "multiagent": result.get("multiagent", False),
        "conversation_id": conv_id,
        "persona": persona_name,
        "source_mode": composed["source_mode"],
        "needs_clarify": composed["needs_clarify"],
        "clarify_options": composed["clarify_options"],
        "error": result.get("error", ""),
    }


def _default_conversation_list() -> dict:
    from campus.conversation.store import ConversationStore
    return {"conversations": ConversationStore().list()}


def _default_conversation_get(conversation_id: str) -> dict:
    from campus.conversation.store import ConversationStore
    conv = ConversationStore().get(conversation_id)
    if not conv:
        return {"ok": False, "error": "conversation not found"}
    conv["ok"] = True
    return conv


def _default_settings_status() -> dict:
    import subprocess
    from campus.runtime.llm_config import real_llm_status
    from campus.runtime.paths import campus_home
    from campus.skills.registry import audit
    skills = audit()
    try:
        branch = subprocess.check_output(["git", "branch", "--show-current"],
                                         cwd=skills.get("repo_root") or None,
                                         text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        branch = ""
    notion = _default_notes_status()
    # Phase 8 Step 5: mobile health checks (real config + readiness, not just env bools)
    try:
        from campus.mobile.feishu import health_check as feishu_health
        feishu = feishu_health()
    except Exception:
        feishu = {"ok": False, "configured": bool(os.environ.get("CAMPUS_FEISHU_CHAT_ID")),
                  "error": "feishu module unavailable"}
    try:
        from campus.mobile.qq_bot_api import QQBotAPIClient
        qq = QQBotAPIClient().health_check()
    except Exception:
        qq = {"ok": False, "configured": bool(os.environ.get("QQ_APP_ID")),
              "error": "qq_bot module unavailable"}
    mobile = {
        "feishu": feishu,
        "qq": qq,
    }
    providers = {
        "github": bool(os.environ.get("GITHUB_TOKEN")),
        "search": bool(os.environ.get("TAVILY_API_KEY") or os.environ.get("SERPAPI_API_KEY")),
    }
    return {
        "ok": True,
        "version": "0.8.0",
        "branch": branch,
        "campus_home": campus_home(),
        "llm": real_llm_status("auto"),
        "skills": skills,
        "notion": notion,
        "mobile": {"ok": feishu.get("ok") or qq.get("ok"), "channels": mobile},
        "providers": providers,
        "smoke_command": "powershell -ExecutionPolicy Bypass -File .\\scripts\\smoke_demo.ps1",
    }


# ---- life backends (Phase 6) ----
# A single shared MemoryPort powers anniversaries + DAILY_LOG. Lazily created so
# importing this module never touches ~/.campus/ (tests inject fakes instead).

_LIFE_MEMORY = None


def _life_memory():
    """Lazily build a JsonFileStore-backed memory for life features (prod path)."""
    global _LIFE_MEMORY
    if _LIFE_MEMORY is None:
        from campus.memory.json_store import JsonFileStore
        _LIFE_MEMORY = JsonFileStore()
    return _LIFE_MEMORY


def _default_calendar_add(req: EventRequest) -> dict:
    from campus.life import calendar_store as cs
    from campus.life.types import CalendarEvent
    import time
    e = cs.add_event(CalendarEvent(
        id="", title=req.title, start=req.start, end=req.end, rrule=req.rrule,
        location=req.location, note=req.note), now=int(time.time()))
    return {"ok": True, "id": e.id, **e.to_dict()}


def _default_calendar_list(start: Optional[str], end: Optional[str]) -> dict:
    from campus.life import calendar_store as cs
    evs = cs.list_events(start, end)
    return {"events": [e.to_dict() for e in evs]}


def _default_calendar_delete(event_id: str) -> dict:
    from campus.life import calendar_store as cs
    return {"ok": cs.delete_event(event_id), "id": event_id}


def _default_anniv_add(req: AnniversaryRequest) -> dict:
    from campus.life import anniversaries as ann
    from campus.life.types import Anniversary
    import time
    a = ann.add_anniversary(_life_memory(),
                            Anniversary(id="", name=req.name, date=req.date,
                                        kind=req.kind, note=req.note),
                            now=int(time.time()))
    return {"ok": True, **a.to_dict()}


def _default_anniv_list() -> dict:
    from campus.life import anniversaries as ann
    return {"anniversaries": [a.to_dict() for a in ann.list_anniversaries(_life_memory())]}


def _default_daily_log_get(day: Optional[str], n: int) -> dict:
    from campus.life import secretary_log as slog
    if day:
        log = slog.get_log(_life_memory(), day)
        return {"logs": [log.to_dict()] if log else []}
    return {"logs": [lg.to_dict() for lg in slog.recent_logs(_life_memory(), n)]}


def _default_daily_log_run() -> dict:
    """Manually trigger one daily tick (preview / catch-up). No push by default."""
    from campus.life.engine import run_daily
    result = run_daily(memory=_life_memory(), push_fn=lambda *a, **k: None)
    return {"ok": True, "reminders_sent": result.reminders_sent,
            "log_id": result.log_id}


def _default_backends() -> Backends:
    return Backends(
        demo_a_run=_default_demo_a,
        demo_b_run=_default_demo_b,
        demo_c_run=_default_demo_c,
        demo_status=_default_demo_status,
        memory_recall=_default_memory_recall,
        onboarding_run=_default_onboarding,
        list_tasks=_default_tasks,
        push_send=_default_push,
        research_add_topic=_default_research_add_topic,
        research_list_topics=_default_research_list_topics,
        research_refresh=_default_research_refresh,
        research_runs=_default_research_runs,
        notion_sync=_default_notion_sync,
        notes_status=_default_notes_status,
        calendar_add=_default_calendar_add,
        calendar_list=_default_calendar_list,
        calendar_delete=_default_calendar_delete,
        anniv_add=_default_anniv_add,
        anniv_list=_default_anniv_list,
        daily_log_get=_default_daily_log_get,
        daily_log_run=_default_daily_log_run,
        agent_run=_default_agent_run,
        agent_list_runs=_default_agent_list_runs,
        agent_get_run=_default_agent_get_run,
        settings_status=_default_settings_status,
    )


def create_app(backends: Optional[Backends] = None,
               with_scheduler: Optional[bool] = None) -> FastAPI:
    """Build the FastAPI app.

    ``with_scheduler``: start the background reminder loop? Defaults to the
    inverse of ``CAMPUS_DISABLE_SCHEDULER`` env var (so tests that don't touch
    it get the loop ON in prod, OFF when the env flag is set). Pass False to
    force-disable (e.g. in TestClient suites).
    """
    # Phase 8 Step 7: logging + prod config
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger = logging.getLogger("campus")

    is_prod = os.environ.get("CAMPUS_ENV", "dev").lower() == "prod"
    kwargs = {"title": "Campus-Agent API", "version": "0.8.0"}
    if is_prod:
        kwargs["docs_url"] = None      # disable /docs (Swagger) in prod
        kwargs["redoc_url"] = None     # disable /redoc in prod
    app = FastAPI(**kwargs)
    app.state.backends = backends or _default_backends()
    app.state.scheduler_thread = None
    app.state.scheduler_stop = None

    # Phase 8 Step 7: CORS (configurable for production)
    from fastapi.middleware.cors import CORSMiddleware
    cors_origins = os.environ.get("CAMPUS_CORS_ORIGINS",
                                  "http://localhost:5173,http://127.0.0.1:5173").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in cors_origins if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("Campus-Agent API starting (env=%s, version=0.8.0)",
                os.environ.get("CAMPUS_ENV", "dev"))

    @app.get("/health")
    def health():
        """Liveness + readiness check. Verifies CAMPUS_HOME is writable."""
        import os, tempfile
        from campus.runtime.paths import campus_home
        try:
            home = campus_home()
            os.makedirs(home, exist_ok=True)
            # writable check
            test_file = os.path.join(home, ".health_probe")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            return {"ok": True, "service": "campus-api", "version": "0.8.0",
                    "campus_home": home, "ready": True}
        except Exception as e:
            return {"ok": True, "service": "campus-api", "ready": False, "error": str(e)}

    @app.post("/demo_b/run")
    def demo_b_run(req: DemoBRequest):
        return app.state.backends.demo_b_run(req)

    @app.post("/demo_a/run")
    def demo_a_run(req: DemoARequest):
        return app.state.backends.demo_a_run(req)

    @app.post("/demo_c/run")
    def demo_c_run(req: DemoCRequest):
        return app.state.backends.demo_c_run(req)

    @app.get("/demo/status")
    def demo_status():
        return app.state.backends.demo_status()

    @app.post("/agent/run")
    def agent_run(req: AgentRunRequest):
        b = app.state.backends.agent_run
        return b(req) if b else _default_agent_run(req)

    @app.get("/agent/runs")
    def agent_runs():
        b = app.state.backends.agent_list_runs
        return b() if b else _default_agent_list_runs()

    @app.get("/agent/runs/{run_id}")
    def agent_get_run(run_id: str):
        b = app.state.backends.agent_get_run
        return b(run_id) if b else _default_agent_get_run(run_id)

    @app.post("/agent/chat")
    def agent_chat(req: AgentChatRequest):
        """Chat-first endpoint: natural-language assistant reply over /agent/run."""
        return _default_agent_chat(req)

    @app.get("/agent/conversations")
    def agent_conversations():
        return _default_conversation_list()

    @app.get("/agent/conversations/{conversation_id}")
    def agent_conversation(conversation_id: str):
        return _default_conversation_get(conversation_id)

    @app.get("/runs")
    def list_runs():
        b = app.state.backends.agent_list_runs
        if b:
            return b()
        return _default_agent_list_runs()

    @app.post("/memory")
    def memory(q: MemoryQuery):
        return {"results": app.state.backends.memory_recall(q.query, q.k)}

    @app.post("/onboarding")
    def onboarding(req: OnboardingRequest):
        return app.state.backends.onboarding_run(req.answers)

    @app.get("/profile")
    def profile():
        return app.state.backends.onboarding_run({})

    @app.get("/tasks")
    def tasks():
        return {"tasks": app.state.backends.list_tasks()}

    @app.get("/settings/status")
    def settings_status():
        b = app.state.backends.settings_status
        return b() if b else _default_settings_status()

    @app.post("/push")
    def push(req: PushRequest):
        return app.state.backends.push_send(req.channel, req.target, req.message)

    @app.post("/research/topics")
    def research_add_topic(req: ResearchTopicRequest):
        b = app.state.backends.research_add_topic
        return b(req) if b else {"ok": False, "error": "research backend not configured"}

    @app.get("/research/topics")
    def research_list_topics():
        b = app.state.backends.research_list_topics
        return b() if b else {"topics": []}

    @app.post("/research/topics/{topic_id}/refresh")
    def research_refresh(topic_id: str, req: ResearchRefreshRequest):
        b = app.state.backends.research_refresh
        return b(topic_id, req) if b else {"ok": False, "error": "research backend not configured"}

    @app.get("/research/runs")
    def research_runs():
        b = app.state.backends.research_runs
        return b() if b else {"runs": []}

    @app.post("/notes/notion/sync")
    def notion_sync(req: NotionSyncRequest):
        b = app.state.backends.notion_sync
        return b(req) if b else {"ok": False, "error": "notes backend not configured"}

    @app.get("/notes/status")
    def notes_status():
        b = app.state.backends.notes_status
        return b() if b else {"ok": False}

    @app.get("/notes/notion/list")
    def notes_notion_list(limit: int = 20):
        from campus.notes import notion
        return notion.list_notes(limit=limit)

    # ---- Zotero integration (Phase 9 — GOAL.md 文献管理) ----
    @app.get("/notes/zotero/status")
    def zotero_status():
        from campus.notes import zotero
        return zotero.status()

    @app.post("/notes/zotero/sync")
    def zotero_sync(req: ZoteroSyncRequest):
        from campus.notes import zotero
        return zotero.sync_papers(req.papers, req.mode)

    @app.post("/notes/zotero/search")
    def zotero_search(req: ZoteroSearchRequest):
        from campus.notes import zotero
        return zotero.search(req.query, req.limit)

    # ---- Phase 7 product routes ----
    @app.post("/learning/flashcards")
    def learning_flashcards(req: FlashcardsRequest):
        from campus import phase7
        return phase7.flashcards(req.topic, req.source_text, req.count, mode=req.mode)

    @app.post("/learning/deadlines")
    def learning_deadline_add(req: DeadlineRequest):
        from campus import phase7
        return phase7.add_deadline(req.title, req.due, req.course, req.note)

    @app.get("/learning/deadlines")
    def learning_deadlines():
        from campus import phase7
        return phase7.list_deadlines()

    @app.post("/learning/quiz/run")
    def learning_quiz_run(req: QuizRunRequest):
        from campus import phase7
        return phase7.quiz_run(req.topic, req.count, req.source_text, mode=req.mode)

    @app.post("/learning/quiz/grade")
    def learning_quiz_grade(req: QuizGradeRequest):
        from campus import phase7
        return phase7.quiz_grade(req.topic, req.answers)

    @app.get("/learning/dashboard")
    def learning_dashboard():
        from campus import phase7
        return phase7.learning_dashboard()

    @app.post("/research/idea")
    def research_idea(req: ResearchIdeaRequest):
        from campus import phase7
        return phase7.research_idea(req.idea, req.mode)

    @app.post("/research/github/trending")
    def research_github(req: GithubTrendingRequest):
        from campus import phase7
        return phase7.github_trending(req.topic, req.language, mode=req.mode)

    @app.post("/research/format/check")
    def research_format(req: FormatCheckRequest):
        from campus import phase7
        return phase7.format_check(req.title, req.target, req.manuscript)

    @app.post("/life/health")
    def life_health(req: HealthRequest):
        from campus import phase7
        return phase7.health_record(req.mood, req.sleep_hours, req.exercise, req.note)

    @app.get("/life/health")
    def life_health_list():
        from campus import phase7
        return phase7.health_list()

    @app.post("/life/travel_plan")
    def life_travel(req: TravelPlanRequest):
        from campus import phase7
        return phase7.travel_plan(req.destination, req.days, req.budget, req.preferences, mode=req.mode)

    @app.get("/life/campus_guide")
    def life_guide(query: str = ""):
        from campus import phase7
        return phase7.campus_guide(query)

    @app.post("/club/meeting_minutes")
    def club_minutes(req: ClubMinutesRequest):
        from campus import phase7
        return phase7.meeting_minutes(req.topic, req.notes, mode=req.mode)

    @app.post("/club/recruiting_copy")
    def club_recruiting(req: RecruitingCopyRequest):
        from campus import phase7
        return phase7.recruiting_copy(req.org, req.audience, req.tone, mode=req.mode)

    @app.post("/club/email_draft")
    def club_email(req: EmailDraftRequest):
        from campus import phase7
        return phase7.email_draft(req.purpose, req.recipient, req.context, mode=req.mode)

    @app.post("/career/jobs/search")
    def career_jobs_search(req: JobSearchRequest):
        from campus import phase7
        return phase7.job_search(req.query, req.city, req.mode)

    @app.post("/career/jobs/save")
    def career_job_save(req: JobSaveRequest):
        from campus import phase7
        return phase7.save_job(req.job)

    @app.get("/career/jobs")
    def career_jobs():
        from campus import phase7
        return phase7.list_jobs()

    @app.post("/career/interview_plan")
    def career_interview(req: InterviewPlanRequest):
        from campus import phase7
        return phase7.interview_plan(req.role, req.days, req.background, mode=req.mode)

    @app.post("/career/interview/practice")
    def career_interview_practice(req: InterviewPracticeRequest):
        from campus import phase7
        return phase7.interview_practice(req.role, req.question, req.answer, req.background)

    @app.post("/career/interview/reflect")
    def career_interview_reflect(req: InterviewReflectRequest):
        from campus import phase7
        return phase7.interview_reflect(req.role, req.reflection, req.practice_run_id, req.tags)

    @app.get("/club/export_status")
    def club_export_status():
        from campus import phase7
        return phase7.export_status()

    @app.post("/learning/quiz/daily")
    def learning_quiz_daily(topic: str = "", count: int = 5):
        from campus import phase7
        return phase7.quiz_daily(topic, count)

    # ---- auto-learn (Phase 8 Step 4) ----
    @app.post("/agent/runs/{run_id}/correction")
    def submit_correction(run_id: str, req: CorrectionRequest):
        from campus.meta_agent.auto_learn import CorrectionStore
        store = CorrectionStore()
        c = store.add(run_id=run_id, domain=req.domain or "",
                      original=req.original, corrected=req.corrected, reason=req.reason)
        return {"ok": True, "correction": c.to_dict(), "total_corrections": store.count()}

    @app.get("/agent/corrections")
    def list_corrections(include_processed: bool = True):
        from campus.meta_agent.auto_learn import CorrectionStore
        store = CorrectionStore()
        return {"corrections": store.list(include_processed=include_processed),
                "total": store.count()}

    @app.post("/admin/auto-learn")
    def trigger_auto_learn(use_llm: bool = True):
        from campus.meta_agent.auto_learn import AutoLearner
        learner = AutoLearner()
        report = learner.run(use_llm=use_llm)
        return report.to_dict()

    @app.get("/agent/skills")
    def list_auto_skills():
        from campus.meta_agent.auto_learn import SkillCreator
        sc = SkillCreator()
        return {"skills": sc.list_skills()}

    # ---- agent name (Phase 8 Step 9) ----
    @app.get("/agent/name")
    def get_agent_name():
        from campus.runtime.paths import state_dir
        import os, json
        path = os.path.join(state_dir(), "agent_config.json")
        config = {}
        try:
            with open(path, encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            pass
        return {"ok": True, "name": config.get("name", "Campus"), "config": config}

    @app.post("/agent/name")
    def set_agent_name(req: AgentNameRequest):
        from campus.runtime.paths import state_dir
        import os, json
        path = os.path.join(state_dir(), "agent_config.json")
        config = {}
        try:
            with open(path, encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            pass
        config["name"] = req.name.strip()[:40] or "Campus"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return {"ok": True, "name": config["name"]}

    # ---- life routes (Phase 6) ----
    @app.post("/calendar")
    def calendar_add(req: EventRequest):
        b = app.state.backends.calendar_add
        if b is None:
            return {"ok": False, "error": "calendar backend not configured"}
        return b(req)

    @app.get("/calendar")
    def calendar_list(start: Optional[str] = None, end: Optional[str] = None):
        b = app.state.backends.calendar_list
        if b is None:
            return {"events": []}
        return b(start, end)

    @app.delete("/calendar/{event_id}")
    def calendar_delete(event_id: str):
        b = app.state.backends.calendar_delete
        if b is None:
            return {"ok": False, "error": "calendar backend not configured"}
        return b(event_id)

    @app.post("/anniversaries")
    def anniv_add(req: AnniversaryRequest):
        b = app.state.backends.anniv_add
        if b is None:
            return {"ok": False, "error": "anniversary backend not configured"}
        return b(req)

    @app.get("/anniversaries")
    def anniv_list():
        b = app.state.backends.anniv_list
        if b is None:
            return {"anniversaries": []}
        return b()

    @app.get("/daily_log")
    def daily_log_get(date: Optional[str] = None, n: int = 7):
        b = app.state.backends.daily_log_get
        if b is None:
            return {"logs": []}
        return b(date, n)

    @app.post("/daily_log/run")
    def daily_log_run():
        b = app.state.backends.daily_log_run
        if b is None:
            return {"ok": False, "error": "daily-log backend not configured"}
        return b()

    # ---- mobile inbound command channel (Phase 8 — GOAL.md 移动端对话) ----
    @app.post("/mobile/command")
    def mobile_command(body: dict = None):
        """Receive a user command from mobile (Feishu/QQ), run agent, reply + persist.

        Body: {"message": "...", "channel": "feishu|qq", "target": "<chat_id>"}
        Returns: {"ok", "reply", "run_id", "artifacts", "pushed"}
        """
        from campus.mobile.inbound import handle_mobile_command
        body = body or {}
        return handle_mobile_command(
            message=body.get("message", ""),
            channel=body.get("channel", "feishu"),
            target=body.get("target"),
        )

    @app.post("/mobile/webhook/feishu")
    def mobile_webhook_feishu(body: dict = None):
        """Feishu event webhook: extract user message → run agent → push reply.

        Accepts Feishu's event format ({event: {message: {content}}}) and
        dispatches to handle_mobile_command. The reply is pushed back to the
        same chat via the configured push channel.
        """
        from campus.mobile.inbound import handle_mobile_command
        body = body or {}
        # Feishu event format: {"event": {"message": {"content": "...", "chat_id": "..."}}}
        event = body.get("event", body)
        msg_raw = event.get("message", {}).get("content", "") or event.get("text", "")
        # Feishu wraps content as JSON {"text":"..."}
        if msg_raw.startswith("{"):
            try:
                msg_raw = json.loads(msg_raw).get("text", msg_raw)
            except Exception:
                pass
        chat_id = event.get("message", {}).get("chat_id", "") or os.environ.get("CAMPUS_FEISHU_CHAT_ID", "")
        if not msg_raw:
            return {"ok": False, "error": "no message in webhook payload"}
        return handle_mobile_command(
            message=msg_raw,
            channel="feishu",
            target=chat_id,
        )

    @app.get("/mobile/commands")
    def mobile_command_history():
        """List recent mobile command history (for debugging/audit)."""
        import json as _json
        from campus.runtime.paths import state_dir
        path = os.path.join(state_dir(), "mobile_commands.json")
        try:
            with open(path, encoding="utf-8") as f:
                return {"ok": True, "commands": _json.load(f)}
        except Exception:
            return {"ok": True, "commands": []}

    # ---- background reminder loop ----
    enable = with_scheduler
    if enable is None:
        enable = not os.environ.get("CAMPUS_DISABLE_SCHEDULER")
    if enable:
        start_scheduler(app)

    # Phase 8 Step 7: serve built frontend (production) if dist/ exists
    import os.path as _osp
    _frontend_dist = _osp.join(_osp.dirname(_osp.dirname(_osp.dirname(_osp.abspath(__file__)))), "frontend", "dist")
    if _osp.isdir(_frontend_dist):
        from fastapi.staticfiles import StaticFiles
        app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")

    return app


# ---- background scheduler -----------------------------------------------------

_SCHEDULER_INTERVAL = 60.0   # seconds between ticks


def start_scheduler(app: FastAPI, interval: float = _SCHEDULER_INTERVAL) -> None:
    """Spawn a daemon thread that runs ``life.engine.run_daily`` every ``interval``.

    Idempotent: a no-op if this app already has a running scheduler. Stores the
    thread + a stop Event on ``app.state`` so ``stop_scheduler`` can join it.
    The loop swallows all exceptions per tick so a transient error never kills
    the thread; push failures are already non-raising (campus.mobile.cli.push).
    """
    import threading
    if getattr(app.state, "scheduler_thread", None) is not None:
        return  # already running
    stop = threading.Event()
    app.state.scheduler_stop = stop

    def _loop():
        from campus.life.engine import run_daily
        while not stop.wait(interval):
            try:
                run_daily(memory=_life_memory())
            except Exception:
                pass  # never let the scheduler die; next tick retries
            # Phase 8 Step 2: nightly memory compression (once per calendar day)
            try:
                _maybe_compress_memory()
            except Exception:
                pass
            # Phase 8 Step 4: nightly auto-learn (once per calendar day)
            try:
                _maybe_auto_learn()
            except Exception:
                pass

    t = threading.Thread(target=_loop, name="campus-life-scheduler", daemon=True)
    app.state.scheduler_thread = t
    t.start()


def stop_scheduler(app: FastAPI, timeout: float = 5.0) -> bool:
    """Signal the scheduler to stop and join. Returns True if it joined cleanly."""
    stop = getattr(app.state, "scheduler_stop", None)
    t = getattr(app.state, "scheduler_thread", None)
    if stop is not None:
        stop.set()
    if t is not None:
        t.join(timeout=timeout)
        app.state.scheduler_thread = None
        return not t.is_alive()
    return True


# ---- nightly memory compression (Phase 8 Step 2) -------------------------------

_LAST_COMPRESS_DAY = None


def _maybe_compress_memory() -> None:
    """Run memory compress + prune once per calendar day (idempotent guard).

    Sediments old TASK_LOG / DAILY_LOG records into a PREFERENCES summary and
    prunes records older than the retention window (pinned records always kept).
    Uses the default (no-LLM) summarizer to stay deterministic + free; a real LLM
    summarizer can be injected later. Mirrors the ``reminders._sent_today`` day-dedup
    pattern so the 60s scheduler tick only fires this once per day.
    """
    global _LAST_COMPRESS_DAY
    import time as _t
    today = _t.strftime("%Y-%m-%d")
    if _LAST_COMPRESS_DAY == today:
        return
    _LAST_COMPRESS_DAY = today
    try:
        from campus.memory.json_store import JsonFileStore
        from campus.memory.compress import compress, prune_by_window
        from campus.memory.types import DAILY_LOG, PREFERENCES, TASK_LOG
        store = JsonFileStore()
        now = int(_t.time())
        retention = 90 * 86400  # 90 days
        # gather old non-pinned TASK_LOG + DAILY_LOG records for compression
        old_recs = [r for r in store.all()
                    if r.layer in (TASK_LOG, DAILY_LOG) and not r.pinned
                    and (now - (r.created_at or 0)) > 7 * 86400]  # > 7 days old
        if old_recs:
            sediment = compress(old_recs, created_at=now)
            if sediment is not None:
                store.remember(layer=PREFERENCES, key=f"sediment-{today}",
                               content=sediment.content,
                               metadata={"sedimented_from": len(old_recs),
                                         "sediment_date": today})
        # prune very old non-pinned records
        all_recs = store.all()
        kept = prune_by_window(all_recs, now, retention)
        pruned_ids = {r.id for r in all_recs} - {r.id for r in kept}
        for rid in pruned_ids:
            store.forget(rid)
    except Exception:
        pass  # never let compression kill the scheduler


_LAST_AUTOLEARN_DAY = None


def _maybe_auto_learn() -> None:
    """Run auto-learn once per calendar day (idempotent day-dedup guard).

    Reviews unprocessed corrections, classifies them (LLM if available, else
    heuristic), and writes derived preferences/skills/knowledge. Uses the same
    day-dedup pattern as ``_maybe_compress_memory``.
    """
    global _LAST_AUTOLEARN_DAY
    import time as _t
    today = _t.strftime("%Y-%m-%d")
    if _LAST_AUTOLEARN_DAY == today:
        return
    _LAST_AUTOLEARN_DAY = today
    try:
        from campus.meta_agent.auto_learn import AutoLearner
        learner = AutoLearner()
        # use_llm=True, but AutoLearner falls back to heuristic if LLM unavailable
        learner.run(use_llm=True)
    except Exception:
        pass  # never let auto-learn kill the scheduler


# module-level app for ``uvicorn campus.api.server:app``.
# Built WITHOUT the background scheduler: importing this module (as tests and
# many callers do) must not spawn a thread. Production callers that want the
# reminder loop should call ``create_app(with_scheduler=True)`` explicitly, or
# call ``start_scheduler(app)`` on an existing app.
app = create_app(with_scheduler=False)
