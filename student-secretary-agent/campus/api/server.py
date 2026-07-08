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

from campus.api.types import DemoBRequest, MemoryQuery, OnboardingRequest, PushRequest

__all__ = ["Backends", "create_app", "app"]


@dataclass
class Backends:
    """Injectable service callables. Any left None uses a sane default."""
    demo_b_run: Callable[[DemoBRequest], dict]
    memory_recall: Callable[[str, int], list]
    onboarding_run: Callable[[dict], dict]
    list_tasks: Callable[[], list]
    push_send: Callable[[str, Optional[str], str], dict]


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


def _default_backends() -> Backends:
    return Backends(
        demo_b_run=_default_demo_b,
        memory_recall=_default_memory_recall,
        onboarding_run=_default_onboarding,
        list_tasks=_default_tasks,
        push_send=_default_push,
    )


def create_app(backends: Optional[Backends] = None) -> FastAPI:
    app = FastAPI(title="Campus-Agent API", version="0.5.0")
    app.state.backends = backends or _default_backends()

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

    return app


# module-level app for ``uvicorn campus.api.server:app``
app = create_app()
