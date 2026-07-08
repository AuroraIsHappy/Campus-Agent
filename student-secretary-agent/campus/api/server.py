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
    DemoBRequest, MemoryQuery, OnboardingRequest, PushRequest,
    EventRequest, AnniversaryRequest, LogQuery,
)

__all__ = ["Backends", "create_app", "app", "start_scheduler", "stop_scheduler"]


@dataclass
class Backends:
    """Injectable service callables. Any left None uses a sane default."""
    demo_b_run: Callable[[DemoBRequest], dict]
    memory_recall: Callable[[str, int], list]
    onboarding_run: Callable[[dict], dict]
    list_tasks: Callable[[], list]
    push_send: Callable[[str, Optional[str], str], dict]
    # life (Phase 6) — Optional so phase-5 callers that omit them still work
    calendar_add: Optional[Callable[[EventRequest], dict]] = None
    calendar_list: Optional[Callable[[Optional[str], Optional[str]], dict]] = None
    calendar_delete: Optional[Callable[[str], dict]] = None
    anniv_add: Optional[Callable[[AnniversaryRequest], dict]] = None
    anniv_list: Optional[Callable[[], dict]] = None
    daily_log_get: Optional[Callable[[Optional[str], int], dict]] = None
    daily_log_run: Optional[Callable[[], dict]] = None


# ---- default backends (real campus libs; deterministic where possible) ----

def _default_demo_b(req: DemoBRequest) -> dict:
    from campus.demo_b import pipeline as _p
    r = _p.run_demo_b(req.path, req.exam_date, free_minutes=req.free_minutes,
                      start_date=req.start_date, topic=req.topic)
    return _result_dict(r)


def _result_dict(r) -> dict:
    return {
        "ok": r.ok, "run_dir": r.run_dir, "final_status": r.final_status,
        "extraction_rate": r.extraction_rate, "kg_nodes": r.kg_nodes,
        "resource_count": r.resource_count, "plan_days": r.plan_days,
    }


def _default_memory_recall(query: str, k: int) -> list:
    return []  # production wires a JsonFileStore; tests inject


def _default_onboarding(answers: dict) -> dict:
    # production: campus.meta_agent.onboarding wizard; deterministic canned default
    return {"ok": True, "profile": {"identity": answers.get("identity", ""),
            "major": answers.get("major", ""), "persona": answers.get("persona", "default")}}


def _default_tasks() -> list:
    return []  # production: campus.runtime kanban; tests inject


def _default_push(channel: str, target: Optional[str], message: str) -> dict:
    try:
        from campus.mobile.cli import push as _push  # real if campus.mobile exists
        receipt = _push(channel, target, message)
        return {"ok": receipt.ok, "channel": receipt.channel,
                "target": receipt.target, "error": receipt.error}
    except Exception as e:
        return {"ok": False, "channel": channel, "target": target, "error": str(e)}


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
        demo_b_run=_default_demo_b,
        memory_recall=_default_memory_recall,
        onboarding_run=_default_onboarding,
        list_tasks=_default_tasks,
        push_send=_default_push,
        calendar_add=_default_calendar_add,
        calendar_list=_default_calendar_list,
        calendar_delete=_default_calendar_delete,
        anniv_add=_default_anniv_add,
        anniv_list=_default_anniv_list,
        daily_log_get=_default_daily_log_get,
        daily_log_run=_default_daily_log_run,
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

    @app.get("/runs")
    def list_runs():
        base = os.path.expanduser("~/.campus/runs")
        if not os.path.isdir(base):
            return {"runs": []}
        return {"runs": sorted(os.listdir(base))}

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

    @app.post("/push")
    def push(req: PushRequest):
        return app.state.backends.push_send(req.channel, req.target, req.message)

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
