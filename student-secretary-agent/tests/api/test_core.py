"""API unit tests: TestClient against create_app with injected fake backends.

Deterministic -- no Hermes / no network / no real model. P5-API1.
"""
import os
import sys
import uuid

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from fastapi.testclient import TestClient

from campus.api.server import Backends, create_app
from campus.api.types import DemoARequest, DemoBRequest, DemoCRequest


def _fake_backends():
    def demo_b(req: DemoBRequest):
        return {"ok": True, "run_dir": "/tmp/fake", "final_status": "delivered",
                "extraction_rate": 1.0, "kg_nodes": 5, "resource_count": 4,
                "plan_days": 10}
    return Backends(
        demo_a_run=lambda req: {"ok": True, "mode": req.mode, "run_dir": "/tmp/demo-a",
                                "outreach_count": 3, "email_segments": 3},
        demo_b_run=demo_b,
        demo_c_run=lambda req: {"ok": True, "mode": req.mode, "run_dir": "/tmp/demo-c",
                                "recommendation": "Official docs", "days": req.days,
                                "quiz_questions": req.quiz_n},
        demo_status=lambda: {"ok": True, "vendor": ["academic-search"], "missing_core": []},
        memory_recall=lambda q, k: [{"key": "demo_b/x", "score": 0.9, "snippet": q}],
        onboarding_run=lambda a: {"ok": True, "profile": {"identity": a.get("identity", "stu"),
                                  "major": "cs", "persona": "feynman"}},
        list_tasks=lambda: [{"id": "t1", "title": "demo_b", "status": "done"}],
        push_send=lambda ch, tg, msg: {"ok": True, "channel": ch, "target": tg, "error": ""},
        research_add_topic=lambda req: {"ok": True, "topic": {"id": "r1", "title": req.title}},
        research_list_topics=lambda: {"topics": [{"id": "r1", "title": "AI"}]},
        research_refresh=lambda tid, req: {"ok": True, "topic_id": tid, "papers": [], "summary": "ok"},
        research_runs=lambda: {"runs": [{"topic_id": "r1", "summary": "ok"}]},
        notion_sync=lambda req: {"ok": True, "local_path": "/tmp/note.md", "notion_ok": False},
        notes_status=lambda: {"ok": False, "token_configured": False},
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


def test_demo_a_run():
    r = client().post("/demo_a/run", json={"topic": "低碳实践", "mode": "offline"})
    assert r.status_code == 200
    assert r.json()["ok"] is True and r.json()["outreach_count"] == 3


def test_demo_c_run_and_status():
    c = client()
    r = c.post("/demo_c/run", json={"goal": "学线性代数", "days": 7, "quiz_n": 2})
    assert r.status_code == 200
    assert r.json()["ok"] is True and r.json()["days"] == 7
    st = c.get("/demo/status")
    assert st.status_code == 200 and st.json()["ok"] is True


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


def test_agent_routes_fake_backend_shape(monkeypatch):
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                                        ".campus-test", uuid.uuid4().hex))
    monkeypatch.setenv("CAMPUS_HOME", base)
    c = client()
    r = c.post("/agent/run", json={"message": "我想学 Linux，帮我安排 30 天计划"})
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True
    assert j["intent"] == "learning_plan"
    assert j["domain"] == "learning"
    assert j["selected_workflow"] == "demo_c_learning_plan"
    rid = j["run_id"]
    assert c.get("/agent/runs").json()["runs"]
    detail = c.get(f"/agent/runs/{rid}").json()
    assert detail["ok"] is True and detail["id"] == rid


def test_settings_status_shape():
    r = client().get("/settings/status")
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True
    assert "campus_home" in j
    assert "llm" in j and "skills" in j and "notion" in j


def test_push():
    r = client().post("/push", json={"channel": "feishu", "message": "hi"})
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True and j["channel"] == "feishu"


def test_research_and_notes_routes():
    c = client()
    add = c.post("/research/topics", json={"title": "LLM agents", "query": "agent papers"})
    assert add.status_code == 200 and add.json()["ok"] is True
    assert c.get("/research/topics").json()["topics"][0]["id"] == "r1"
    digest = c.post("/research/topics/r1/refresh", json={"mode": "offline"}).json()
    assert digest["ok"] is True
    assert c.get("/research/runs").json()["runs"][0]["topic_id"] == "r1"
    sync = c.post("/notes/notion/sync", json={"digest": digest, "mode": "local"}).json()
    assert sync["ok"] is True and sync["notion_ok"] is False
    assert "token_configured" in c.get("/notes/status").json()


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


def test_default_backends_offline_demo_smoke(monkeypatch):
    """Default API backends can run the offline demo chain inside CAMPUS_HOME."""
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                                        ".campus-test", uuid.uuid4().hex))
    monkeypatch.setenv("CAMPUS_HOME", base)
    c = TestClient(create_app(with_scheduler=False))
    a = c.post("/demo_a/run", json={"topic": "低碳实践", "region": "北京高校社区",
                                    "mode": "offline"}).json()
    assert a["ok"] is True
    assert a["mode"] == "offline"
    assert os.path.isdir(a["run_dir"])
    assert any(p.endswith("proposal.md") for p in a["artifacts"])

    b = c.post("/demo_c/run", json={"goal": "入门线性代数", "days": 3,
                                    "quiz_n": 2, "mode": "offline"}).json()
    assert b["ok"] is True
    assert b["mode"] == "offline"
    assert os.path.isdir(b["run_dir"])

    add = c.post("/research/topics", json={"title": "LLM agents", "query": "agent papers"}).json()
    digest = c.post(f"/research/topics/{add['topic']['id']}/refresh", json={"mode": "auto"}).json()
    assert digest["ok"] is True
    assert digest["source_mode"] in {"real", "fallback_offline", "offline"}
    assert digest["note_path"] and os.path.exists(digest["note_path"])


def test_default_agent_run_writes_foundation_stores(monkeypatch):
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                                        ".campus-test", uuid.uuid4().hex))
    monkeypatch.setenv("CAMPUS_HOME", base)
    c = TestClient(create_app(with_scheduler=False))
    r = c.post("/agent/run", json={"message": "我想学 Linux，帮我安排 3 天计划",
                                   "mode": "offline",
                                   "context": {"days": 3}}).json()
    assert r["ok"] is True
    assert r["domain"] == "learning"
    run_id = r["run_id"]
    detail = c.get(f"/agent/runs/{run_id}").json()
    assert detail["ok"] is True
    assert detail["status"] == "done"
    names = {a["name"] for a in detail["artifacts"]}
    assert {"Plan.md", "Status.md", "Verification.md", "run_result.json", "artifact_manifest.json"} <= names
    assert os.path.exists(os.path.join(base, "state", "runs.json"))
    tasks = c.get("/tasks").json()["tasks"]
    assert any(t["run_id"] == run_id for t in tasks)
