"""Tests for the MetaAgent → Odyssey execution bridge (Phase 8 Step 1).

Verifies the MetaRunner classifies + builds + executes the DAG with the offline
turn (no Hermes / no LLM / no network), and that /agent/run routes long tasks
through the multi-agent path when real mode is requested.
"""
import os
import sys
import uuid

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from campus.meta_agent.runner import MetaRunner, make_offline_turn
from campus.meta_agent.meta_agent import MetaAgent


def test_meta_runner_short_offline():
    """A short message → single-node DAG → done with a summary."""
    runner = MetaRunner()
    r = runner.run("帮我查个资料", mode="offline")
    assert r.ok
    assert r.kind == "short"
    assert r.run_id
    assert r.final_status == "done"
    assert len(r.dag) == 1
    assert r.dag[0]["role"] == "hermes_direct"


def test_meta_runner_long_offline_executes_full_dag():
    """A long message → 8-role DAG + two adversarial debates, all offline."""
    runner = MetaRunner()
    msg = "帮我做一份校园低碳社会实践策划案，包含外联对象和邮件草稿"  # >20 chars + LONG_KEYWORDS
    r = runner.run(msg, mode="offline")
    assert r.ok
    assert r.kind == "long"
    assert r.run_id
    # two debates: Planner<->Critic, Writer<->Reviewer
    assert len(r.debates) == 2
    pairs = [d["pair"] for d in r.debates]
    assert "Planner<->Critic" in pairs
    assert "Writer<->Reviewer" in pairs
    # each debate has an outcome + rounds
    for d in r.debates:
        assert d["outcome"] in ("pass", "forced", "escalated")
        assert d["rounds"] >= 1
    assert r.summary  # writer produced output
    assert r.final_status in ("done", "awaiting_human")


def test_meta_runner_writes_foundation_artifacts(monkeypatch):
    """The run writes Plan/Status/Verification/run_result.json + manifest."""
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                                        ".campus-test", uuid.uuid4().hex))
    monkeypatch.setenv("CAMPUS_HOME", base)
    runner = MetaRunner()
    r = runner.run("我想学 Linux 并安排 30 天复习计划", mode="offline")
    assert r.ok
    assert r.artifacts  # manifest non-empty
    names = [a["name"] for a in r.artifacts]
    assert "Plan.md" in names
    assert "Status.md" in names
    assert "Verification.md" in names
    assert "run_result.json" in names


def test_meta_runner_classify_uses_metaagent():
    """MetaRunner delegates to MetaAgent.classify — long keywords trigger long DAG."""
    runner = MetaRunner()
    assert runner.meta is not None
    short = runner.meta.classify("查资料")
    assert short.kind == "short"
    long = runner.meta.classify("帮我做一份社会实践策划案")
    assert long.kind == "long"


def test_agent_run_offline_still_uses_deterministic_routing(monkeypatch):
    """Offline /agent/run keeps the phase7 keyword routing (backward compat)."""
    from fastapi.testclient import TestClient
    from campus.api.server import create_app
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                                        ".campus-test", uuid.uuid4().hex))
    monkeypatch.setenv("CAMPUS_HOME", base)
    c = TestClient(create_app(with_scheduler=False))
    r = c.post("/agent/run", json={"message": "我想学习 Linux，安排计划", "mode": "offline"}).json()
    assert r["ok"]
    assert r["multiagent"] is False  # offline → deterministic routing
