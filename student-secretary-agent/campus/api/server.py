"""FastAPI app for the Campus frontend (Phase 5).

``create_app(backends=...)`` builds the app; every route delegates to a backend
callable stored in ``app.state.backends``. Default backends call the real campus
libraries (demo_b pipeline, onboarding); tests inject fakes so the TestClient
suite is deterministic (no Hermes / no network / no real model).

Run for real:  ``uvicorn campus.api.server:app`` (after ``create_app()``).
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any, Callable, Optional

from fastapi import FastAPI

from campus.api.types import (
    AgentRunRequest, DemoARequest, DemoBRequest, DemoCRequest, MemoryQuery, OnboardingRequest, PushRequest,
    EventRequest, AnniversaryRequest, LogQuery, ResearchTopicRequest,
    ResearchRefreshRequest, NotionSyncRequest,
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
    r = _p.run_demo_b(req.path, req.exam_date, free_minutes=req.free_minutes,
                      start_date=req.start_date, topic=req.topic)
    return _result_dict(r)


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
    # production: campus.meta_agent.onboarding wizard; deterministic canned default
    return {"ok": True, "profile": {"identity": answers.get("identity", ""),
            "major": answers.get("major", ""), "persona": answers.get("persona", "default")}}


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
    try:
        if domain == "learning":
            days = int(req.context.get("days", 30)) if isinstance(req.context, dict) else 30
            result = _default_demo_c(DemoCRequest(goal=req.message, days=days, mode=req.mode))
        elif domain == "club":
            result = _default_demo_a(DemoARequest(topic=req.message[:80] or "校园活动", mode=req.mode))
        elif domain == "research":
            topic = _default_research_add_topic(ResearchTopicRequest(title=req.message[:80] or "research idea", query=req.message))
            result = _default_research_refresh(topic["topic"]["id"], ResearchRefreshRequest(mode=req.mode))
        else:
            result = {"ok": True, "summary": f"已记录任务：{req.message}", "source_mode": "local"}
        if not result.get("ok", False):
            status = "failed"
            error = result.get("error", "")
    except Exception as e:
        status = "failed"
        error = str(e)
        result = {"ok": False, "error": error}
    imported = artifacts.import_paths(rec.id, result.get("artifacts", []))
    if result.get("run_dir"):
        imported.append(artifacts.write_text(rec.id, "SourceRun.txt", str(result["run_dir"]), "reference"))
    artifacts.write_text(rec.id, "Status.md", f"# Status\n\n- status: {status}\n- error: {error}\n")
    artifacts.write_text(rec.id, "Verification.md", f"# Verification\n\n- local fallback safe: yes\n- result ok: {bool(result.get('ok'))}\n")
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
    }


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
    mobile = {
        "feishu": bool(os.environ.get("CAMPUS_FEISHU_CHAT_ID")),
        "qq": bool(os.environ.get("CAMPUS_QQ_BOT_APP_ID") or os.environ.get("QQ_BOT_APP_ID")),
    }
    providers = {
        "github": bool(os.environ.get("GITHUB_TOKEN")),
        "search": bool(os.environ.get("TAVILY_API_KEY") or os.environ.get("SERPAPI_API_KEY")),
    }
    return {
        "ok": True,
        "version": "0.7.0",
        "branch": branch,
        "campus_home": campus_home(),
        "llm": real_llm_status("auto"),
        "skills": skills,
        "notion": notion,
        "mobile": {"ok": any(mobile.values()), "channels": mobile},
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
    app = FastAPI(title="Campus-Agent API", version="0.6.0")
    app.state.backends = backends or _default_backends()
    app.state.scheduler_thread = None
    app.state.scheduler_stop = None

    @app.get("/health")
    def health():
        return {"ok": True, "service": "campus-api"}

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

    # ---- background reminder loop ----
    enable = with_scheduler
    if enable is None:
        enable = not os.environ.get("CAMPUS_DISABLE_SCHEDULER")
    if enable:
        start_scheduler(app)

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


# module-level app for ``uvicorn campus.api.server:app``.
# Built WITHOUT the background scheduler: importing this module (as tests and
# many callers do) must not spawn a thread. Production callers that want the
# reminder loop should call ``create_app(with_scheduler=True)`` explicitly, or
# call ``start_scheduler(app)`` on an existing app.
app = create_app(with_scheduler=False)
