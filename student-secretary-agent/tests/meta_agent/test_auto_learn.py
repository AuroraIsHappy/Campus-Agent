"""Tests for the auto-learn system (Phase 8 Step 4).

Verifies correction capture, offline heuristic classification, preference/skill
writing, and the API endpoints — all deterministic (no LLM required).
"""
import os
import sys
import uuid

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from campus.meta_agent.auto_learn import (
    CorrectionStore, AutoLearner, SkillCreator, LearnReport,
)


def _isolated(monkeypatch):
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                                        ".campus-test", uuid.uuid4().hex))
    monkeypatch.setenv("CAMPUS_HOME", base)
    return base


def test_correction_store_add_and_list(monkeypatch):
    _isolated(monkeypatch)
    store = CorrectionStore()
    assert store.count() == 0
    c = store.add(run_id="run_1", domain="learning",
                  original="wrong answer", corrected="right answer", reason="factual error")
    assert c.id and c.ts > 0
    assert store.count() == 1
    assert store.unprocessed() == [c]
    store.mark_processed([c.id])
    assert store.unprocessed() == []
    assert store.count() == 1  # still listed, just processed


def test_auto_learner_writes_preference_offline(monkeypatch):
    """Offline (no LLM): a single correction → heuristic → preference written."""
    base = _isolated(monkeypatch)
    store = CorrectionStore()
    store.add(run_id="run_1", domain="life",
              original="plan A", corrected="prefer plan B because shorter", reason="preference")
    learner = AutoLearner(corrections=store)
    report = learner.run(use_llm=False)
    assert report.ok
    assert report.processed == 1
    # single correction → heuristic picks "preference"
    assert report.preferences_written >= 1
    # verify it was written to memory
    from campus.memory.json_store import JsonFileStore
    from campus.memory.types import PREFERENCES
    mem = JsonFileStore()
    prefs = mem.list_layer(PREFERENCES)
    assert any("auto_pref" in p.key for p in prefs)


def test_auto_learner_writes_skill_offline(monkeypatch):
    """Offline: 2+ corrections in same domain → heuristic → skill defect → skill created."""
    base = _isolated(monkeypatch)
    store = CorrectionStore()
    store.add(run_id="r1", domain="club", original="bad minutes", corrected="better minutes", reason="format")
    store.add(run_id="r2", domain="club", original="bad copy", corrected="better copy", reason="tone")
    # point SkillCreator at a temp skills dir
    skills_dir = os.path.join(base, "skills")
    sc = SkillCreator(skills_dir=skills_dir)
    learner = AutoLearner(corrections=store, skill_creator=sc)
    report = learner.run(use_llm=False)
    assert report.ok
    assert report.processed == 2
    assert report.skills_created >= 1
    # verify SKILL.md was created
    skills = sc.list_skills()
    assert len(skills) >= 1
    # verify the file exists
    skill_path = os.path.join(skills_dir, skills[0], "SKILL.md")
    assert os.path.isfile(skill_path)
    with open(skill_path, encoding="utf-8") as f:
        content = f.read()
    assert "Auto-learned" in content or "Auto-created" in content


def test_auto_learner_marks_processed(monkeypatch):
    """After running, corrections are marked processed (not re-processed)."""
    _isolated(monkeypatch)
    store = CorrectionStore()
    store.add(run_id="r1", domain="learning", original="x", corrected="y")
    learner = AutoLearner(corrections=store)
    report1 = learner.run(use_llm=False)
    assert report1.processed == 1
    # second run should have nothing to process
    report2 = learner.run(use_llm=False)
    assert report2.processed == 0


def test_skill_creator_update_existing(monkeypatch):
    """Creating a skill that already exists appends instructions (update, not duplicate)."""
    base = _isolated(monkeypatch)
    sc = SkillCreator(skills_dir=os.path.join(base, "skills"))
    r1 = sc.create_or_update(name="test-skill", trigger="test", instructions="v1")
    assert r1["created"] is True
    r2 = sc.create_or_update(name="test-skill", trigger="test2", instructions="v2")
    assert r2["created"] is False  # updated, not created
    with open(r2["path"], encoding="utf-8") as f:
        content = f.read()
    assert "v1" in content and "v2" in content


def test_correction_api_endpoint(monkeypatch):
    """POST /agent/runs/{id}/correction captures a correction."""
    from fastapi.testclient import TestClient
    from campus.api.server import create_app
    _isolated(monkeypatch)
    c = TestClient(create_app(with_scheduler=False))
    r = c.post("/agent/runs/run_123/correction", json={
        "run_id": "run_123", "domain": "learning",
        "original": "wrong", "corrected": "right", "reason": "test"
    }).json()
    assert r["ok"] is True
    assert r["correction"]["run_id"] == "run_123"
    assert r["total_corrections"] >= 1


def test_auto_learn_api_endpoint(monkeypatch):
    """POST /admin/auto-learn triggers the learn cycle."""
    from fastapi.testclient import TestClient
    from campus.api.server import create_app
    base = _isolated(monkeypatch)
    c = TestClient(create_app(with_scheduler=False))
    # seed a correction first
    c.post("/agent/runs/run_1/correction", json={
        "run_id": "run_1", "domain": "life",
        "original": "x", "corrected": "y", "reason": "test"})
    r = c.post("/admin/auto-learn?use_llm=false").json()
    assert r["ok"] is True
    assert r["processed"] >= 1


def test_agent_name_api(monkeypatch):
    """GET/POST /agent/name sets and reads the agent display name."""
    from fastapi.testclient import TestClient
    from campus.api.server import create_app
    _isolated(monkeypatch)
    c = TestClient(create_app(with_scheduler=False))
    # default name
    r = c.get("/agent/name").json()
    assert r["ok"] and r["name"] == "Campus"
    # set a custom name
    r = c.post("/agent/name", json={"name": "小秘"}).json()
    assert r["ok"] and r["name"] == "小秘"
    # read it back
    r = c.get("/agent/name").json()
    assert r["name"] == "小秘"
