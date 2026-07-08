"""API unit tests: TestClient against create_app with injected fake backends.

Deterministic -- no Hermes / no network / no real model. P5-API1.
"""
import os
import sys

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from fastapi.testclient import TestClient

from campus.api.server import Backends, create_app
from campus.api.types import DemoBRequest


def _fake_backends():
    def demo_b(req: DemoBRequest):
        return {"ok": True, "run_dir": "/tmp/fake", "final_status": "delivered",
                "extraction_rate": 1.0, "kg_nodes": 5, "resource_count": 4,
                "plan_days": 10}
    return Backends(
        demo_b_run=demo_b,
        memory_recall=lambda q, k: [{"key": "demo_b/x", "score": 0.9, "snippet": q}],
        onboarding_run=lambda a: {"ok": True, "profile": {"identity": a.get("identity", "stu"),
                                  "major": "cs", "persona": "feynman"}},
        list_tasks=lambda: [{"id": "t1", "title": "demo_b", "status": "done"}],
        push_send=lambda ch, tg, msg: {"ok": True, "channel": ch, "target": tg, "error": ""},
    )


def client():
    return TestClient(create_app(backends=_fake_backends()))


def test_health():
    r = client().get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_demo_b_run():
    r = client().post("/demo_b/run", json={"path": "/tmp/x", "exam_date": "2026-08-15"})
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True and j["kg_nodes"] == 5 and j["plan_days"] == 10


def test_memory():
    r = client().post("/memory", json={"query": "pointers", "k": 3})
    assert r.status_code == 200
    res = r.json()["results"]
    assert len(res) == 1 and res[0]["key"] == "demo_b/x"


def test_onboarding_and_profile():
    c = client()
    r = c.post("/onboarding", json={"answers": {"identity": "Alex", "major": "physics"}})
    assert r.status_code == 200
    assert r.json()["profile"]["identity"] == "Alex"
    p = c.get("/profile")
    assert p.status_code == 200 and "profile" in p.json()


def test_tasks():
    r = client().get("/tasks")
    assert r.status_code == 200
    assert r.json()["tasks"][0]["id"] == "t1"


def test_runs_shape():
    r = client().get("/runs")
    assert r.status_code == 200
    assert "runs" in r.json() and isinstance(r.json()["runs"], list)


def test_push():
    r = client().post("/push", json={"channel": "feishu", "message": "hi"})
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True and j["channel"] == "feishu"


def test_default_app_module_level():
    """The module-level ``app`` builds with default backends (importable)."""
    from campus.api.server import app as _app
    with TestClient(_app) as c:
        assert c.get("/health").json()["ok"] is True
        assert c.get("/profile").status_code == 200
