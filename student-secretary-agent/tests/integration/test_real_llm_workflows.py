"""Integration tests for real-LLM-driven workflows (Phase 8 Step 3).

These require a real GLM key + hermes_cli importable. Marked ``integration`` so
they're skipped by default (``addopts = "-m 'not integration'"``). Run manually::

    .venv/Scripts/python.exe -m pytest tests/integration/test_real_llm_workflows.py -m integration -v

Each test exercises one domain workflow in real mode and asserts the output is
non-template (source_mode == "real_llm") and structurally valid.
"""
import os
import sys
import uuid

import pytest

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _isolated_campus_home(monkeypatch):
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                                        ".campus-test", uuid.uuid4().hex))
    monkeypatch.setenv("CAMPUS_HOME", base)


def _llm_ready() -> bool:
    try:
        from campus.runtime.llm_config import real_llm_status
        return real_llm_status("real")["ok"]
    except Exception:
        return False


@pytest.mark.skipif(not _llm_ready(), reason="GLM key / hermes_cli not available")
def test_real_flashcards():
    from fastapi.testclient import TestClient
    from campus.api.server import create_app
    c = TestClient(create_app(with_scheduler=False))
    r = c.post("/learning/flashcards", json={"topic": "操作系统", "count": 3, "mode": "real"}).json()
    assert r["ok"]
    assert r.get("source_mode") == "real_llm"
    assert len(r["flashcards"]) >= 1
    card = r["flashcards"][0]
    assert card.get("front") and card.get("back")


@pytest.mark.skipif(not _llm_ready(), reason="GLM key / hermes_cli not available")
def test_real_quiz():
    from fastapi.testclient import TestClient
    from campus.api.server import create_app
    c = TestClient(create_app(with_scheduler=False))
    r = c.post("/learning/quiz/run", json={"topic": "计算机网络", "count": 2, "mode": "real"}).json()
    assert r["ok"]
    assert r.get("source_mode") == "real_llm"
    assert len(r["questions"]) >= 1


@pytest.mark.skipif(not _llm_ready(), reason="GLM key / hermes_cli not available")
def test_real_github_trending():
    from fastapi.testclient import TestClient
    from campus.api.server import create_app
    c = TestClient(create_app(with_scheduler=False))
    r = c.post("/research/github/trending", json={"topic": "LLM agent", "mode": "real"}).json()
    assert r["ok"]
    assert r.get("source_mode") == "real_llm"
    assert len(r["items"]) >= 1


@pytest.mark.skipif(not _llm_ready(), reason="GLM key / hermes_cli not available")
def test_real_meeting_minutes():
    from fastapi.testclient import TestClient
    from campus.api.server import create_app
    c = TestClient(create_app(with_scheduler=False))
    r = c.post("/club/meeting_minutes", json={
        "topic": "秋季招新筹备", "notes": "讨论了宣传策略和面试流程", "mode": "real"}).json()
    assert r["ok"]
    assert r.get("source_mode") == "real_llm"
    assert r.get("minutes", {}).get("todo") or r.get("minutes", {}).get("decisions")


@pytest.mark.skipif(not _llm_ready(), reason="GLM key / hermes_cli not available")
def test_real_travel_plan():
    from fastapi.testclient import TestClient
    from campus.api.server import create_app
    c = TestClient(create_app(with_scheduler=False))
    r = c.post("/life/travel_plan", json={"destination": "杭州", "days": 2, "mode": "real"}).json()
    assert r["ok"]
    assert r.get("source_mode") == "real_llm"
    assert len(r["itinerary"]) >= 1


@pytest.mark.skipif(not _llm_ready(), reason="GLM key / hermes_cli not available")
def test_real_interview_plan():
    from fastapi.testclient import TestClient
    from campus.api.server import create_app
    c = TestClient(create_app(with_scheduler=False))
    r = c.post("/career/interview_plan", json={"role": "后端开发实习生", "days": 5, "mode": "real"}).json()
    assert r["ok"]
    assert r.get("source_mode") == "real_llm"
    assert len(r["plan"]) >= 1 or len(r["questions"]) >= 1
