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
    # with_scheduler=False keeps the TestClient suite deterministic (no bg thread)
    return TestClient(create_app(backends=_fake_backends(), with_scheduler=False))


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
    """The module-level ``app`` builds with default backends (importable, no scheduler)."""
    from campus.api.server import app as _app
    with TestClient(_app) as c:
        assert c.get("/health").json()["ok"] is True
        assert c.get("/profile").status_code == 200


# ---- life routes (Phase 6, L-API1) ----

def _life_backends():
    """Backends wired to real campus.life libs but with injected memory + temp calendar."""
    import tempfile
    from campus.memory.in_memory import InMemoryStore
    from campus.life import calendar_store as cs, anniversaries as ann, secretary_log as slog
    from campus.life.types import CalendarEvent, Anniversary, SecretaryLog
    fd, cal_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(cal_path)
    mem = InMemoryStore()

    def cal_add(req):
        e = cs.add_event(CalendarEvent(id="", title=req.title, start=req.start,
                                       end=req.end, rrule=req.rrule,
                                       location=req.location, note=req.note), path=cal_path)
        return {"ok": True, "id": e.id, **e.to_dict()}

    def cal_list(start, end):
        return {"events": [e.to_dict() for e in cs.list_events(start, end, path=cal_path)]}

    def cal_delete(eid):
        return {"ok": cs.delete_event(eid, path=cal_path), "id": eid}

    def a_add(req):
        a = ann.add_anniversary(mem, Anniversary(id="", name=req.name, date=req.date,
                                                 kind=req.kind, note=req.note))
        return {"ok": True, **a.to_dict()}

    def a_list():
        return {"anniversaries": [a.to_dict() for a in ann.list_anniversaries(mem)]}

    def log_get(day, n):
        if day:
            log = slog.get_log(mem, day)
            return {"logs": [log.to_dict()] if log else []}
        return {"logs": [lg.to_dict() for lg in slog.recent_logs(mem, n)]}

    def log_run():
        slog.write_log(mem, SecretaryLog(date="2026-07-09", summary="test"))
        return {"ok": True, "reminders_sent": 0, "log_id": "x"}

    base = _fake_backends()
    base.calendar_add = cal_add
    base.calendar_list = cal_list
    base.calendar_delete = cal_delete
    base.anniv_add = a_add
    base.anniv_list = a_list
    base.daily_log_get = log_get
    base.daily_log_run = log_run
    return base


def test_calendar_add_list_delete():
    c = TestClient(create_app(backends=_life_backends(), with_scheduler=False))
    r = c.post("/calendar", json={"title": "高数课", "start": "2026-07-09T08:00",
                                  "location": "教三301"})
    assert r.status_code == 200 and r.json()["ok"] is True
    eid = r.json()["id"]
    # list (no window returns all)
    lst = c.get("/calendar").json()["events"]
    assert any(e["id"] == eid for e in lst)
    # delete
    d = c.delete(f"/calendar/{eid}").json()
    assert d["ok"] is True


def test_anniversaries_add_list():
    c = TestClient(create_app(backends=_life_backends(), with_scheduler=False))
    r = c.post("/anniversaries", json={"name": "小明", "date": "07-09", "kind": "birthday"})
    assert r.status_code == 200 and r.json()["ok"] is True
    lst = c.get("/anniversaries").json()["anniversaries"]
    assert len(lst) == 1 and lst[0]["name"] == "小明"


def test_daily_log_get_and_run():
    c = TestClient(create_app(backends=_life_backends(), with_scheduler=False))
    # run creates a log
    c.post("/daily_log/run")
    # get by date
    r = c.get("/daily_log", params={"date": "2026-07-09"})
    assert r.status_code == 200
    logs = r.json()["logs"]
    assert len(logs) == 1 and logs[0]["summary"] == "test"
    # recent (n)
    r2 = c.get("/daily_log", params={"n": 7})
    assert len(r2.json()["logs"]) >= 1


def test_life_routes_unconfigured_graceful():
    """When life backends are None, routes return safe empty shapes (not 500)."""
    c = TestClient(create_app(backends=_fake_backends(), with_scheduler=False))
    assert c.get("/calendar").json() == {"events": []}
    assert c.get("/anniversaries").json() == {"anniversaries": []}
    assert c.get("/daily_log").json() == {"logs": []}
    assert c.post("/calendar", json={"title": "x", "start": "2026-07-09T08:00"}).json()["ok"] is False


def test_scheduler_starts_and_stops():
    from campus.api.server import create_app, start_scheduler, stop_scheduler
    app = create_app(backends=_fake_backends(), with_scheduler=False)
    assert app.state.scheduler_thread is None   # not started
    start_scheduler(app, interval=0.01)
    assert app.state.scheduler_thread is not None
    assert stop_scheduler(app) is True           # joined cleanly
    assert app.state.scheduler_thread is None


def test_with_scheduler_true_starts_thread():
    from campus.api.server import create_app, stop_scheduler
    app = create_app(backends=_fake_backends(), with_scheduler=True)
    assert app.state.scheduler_thread is not None
    stop_scheduler(app)
