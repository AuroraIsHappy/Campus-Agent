"""P3 L2 deterministic e2e: full Demo A DAG with a mocked ask_llm.

No Hermes, no LLM, no network (url_opener injected). Asserts A-F1..F4 + A-Q1..Q5
structurally: DAG parents wired, both debates reach a verdict, >=3 outreach
targets with full fields, email segments == target count, final status
awaiting_human (no send), proposal artifact present, checks pass, Verification.md
records both debates.
"""
import json
import os

import campus.runtime.llm_turn as lt
from campus.demo_a import pipeline
from campus.demo_a.types import Brief, SampleSpec

PLAN = ("# Plan\nCheckpoints: Research -> Verify -> Rank -> Write -> Review -> Email.\n"
        "Topic: 航天科普; region: 北京.")
TARGETS_JSON = (
    "```json\n"
    '[{"name":"北京航天博物馆","visit_reason":"航天科普","contact_source":"官网","url":"https://a.example.com"},'
    '{"name":"中国科技馆","visit_reason":"互动展览","contact_source":"官网","url":"https://b.example.com"},'
    '{"name":"中关村创业大街","visit_reason":"创新实践","contact_source":"官网","url":"https://c.example.com"}]\n```')
VERIFIED_JSON = (
    "```json\n"
    '[{"name":"北京航天博物馆","url":"https://a.example.com","verified":true,"evidence":"HTTP 200"},'
    '{"name":"中国科技馆","url":"https://b.example.com","verified":true,"evidence":"HTTP 200"},'
    '{"name":"中关村创业大街","url":"https://c.example.com","verified":true,"evidence":"HTTP 200"}]\n```')
PROPOSAL = (
    "# 社会实践策划案\n\n## 活动背景\n航天科普主题。\n\n## 时间表\n"
    "- 7月10日 北京航天博物馆\n- 7月11日 中国科技馆\n\n"
    "## 预算\n- 交通费: 200\n- 餐饮费: 150\n\n## 安全预案\n配备安全员，购买保险。\n")
EMAILS = ("Subject: 参访申请 — 北京航天博物馆\n尊敬的馆方...\n\n"
          "Subject: 参访申请 — 中国科技馆\n尊敬的馆方...\n\n"
          "Subject: 参访申请 — 中关村创业大街\n尊敬的馆方...\n")


def _fake_ask(prompt, model="glm-4.6", provider="zai", toolsets=None):
    if "Adversarial review of this PLAN" in prompt:
        return ("APPROVE\nPlan covers all checkpoints and fits sample format.", 0)
    if "Adversarial review of this PROPOSAL" in prompt:
        return ("APPROVE\nFormat matches sample; budget/timeline/safety present; "
                "no fabrication.", 0)
    if "checkpointed PLAN" in prompt:
        return (PLAN, 0)
    if "Find >=3 outreach targets" in prompt:
        return (TARGETS_JSON, 0)
    if "confirm the url is real" in prompt:
        return (VERIFIED_JSON, 0)
    if "Score and rank" in prompt:
        return (TARGETS_JSON, 0)
    if "Write the 社会实践策划案" in prompt:
        return (PROPOSAL, 0)
    if "ONE copy-paste outreach email" in prompt:
        return (EMAILS, 0)
    return ("APPROVE\nfallback", 0)


def _sample():
    return SampleSpec(raw="sample", columns=["活动背景", "时间表", "预算", "安全预案"],
                      tone="formal")


def test_demo_a_full_pipeline_deterministic(tmp_path, monkeypatch):
    monkeypatch.setattr(lt, "ask_llm", _fake_ask)
    res = pipeline.run_demo_a(
        _sample(), Brief(topic="航天科普", region="北京", window="2026年7月"),
        run_dir=str(tmp_path), board="campus-demo-a-e2e",
        url_opener=lambda u, t: 200)

    # A-F4: halted in awaiting_human, nothing sent (B1 structural -- no send call)
    assert res.final_status == "awaiting_human", res.final_status
    # A-F2: >=3 outreach targets with full fields
    assert res.outreach_count >= 3
    ranked = json.load(open(os.path.join(str(tmp_path), "ranked_targets.json"),
                            encoding="utf-8"))
    for t in ranked:
        assert {"name", "visit_reason", "contact_source", "url"} <= set(t.keys())
    # A-F3: one email segment per target, draft only
    assert res.email_segments == res.outreach_count
    assert os.path.exists(os.path.join(str(tmp_path), "emails.txt"))
    # A-F1: proposal artifact exists + openable (md always; docx if lib present)
    assert os.path.exists(os.path.join(str(tmp_path), "proposal.md"))
    # A-Q1/Q3/Q4: all rule checks pass
    assert all(c.passed for c in res.checks), [c.detail for c in res.checks]
    # A-Q5: Verification.md records both adversarial debates
    ver = open(os.path.join(str(tmp_path), "Verification.md"), encoding="utf-8").read()
    assert "Planner<->Critic" in ver and "Writer<->Reviewer" in ver
    # both debates reached APPROVE (DEBATE_PASS) in round 1
    assert res.debates[0]["outcome"] == "pass"
    assert res.debates[1]["outcome"] == "pass"
    assert res.ok, [c.detail for c in res.checks]


def test_demo_a_dag_parents_wired(tmp_path, monkeypatch):
    """The downstream chain is a real DAG (parents), not a flat task list."""
    monkeypatch.setattr(lt, "ask_llm", _fake_ask)
    from campus.runtime.in_memory import InMemoryKanban
    kb = InMemoryKanban("campus-demo-a-dag")
    pipeline.run_demo_a(_sample(), Brief(topic="x", region="北京"),
                        run_dir=str(tmp_path), kanban=kb,
                        url_opener=lambda u, t: 200)
    by = {t.assignee: t for t in kb.all_tasks()}
    assert by["researcher"].parents[0] == by["planner"].id
    assert by["source_verifier"].parents[0] == by["researcher"].id
    assert by["source_ranker"].parents[0] == by["source_verifier"].id
    assert by["writer"].parents[0] == by["source_ranker"].id
    assert by["email"].parents[0] == by["writer"].id


def test_demo_a_no_auto_send(tmp_path, monkeypatch):
    """A-F4: the pipeline exposes no send path -- escalate parks the task."""
    monkeypatch.setattr(lt, "ask_llm", _fake_ask)
    import inspect
    from campus.demo_a import pipeline as pl
    src = inspect.getsource(pl)
    assert "smtp" not in src.lower()        # no SMTP import/use
    assert "smtplib" not in src.lower()
    res = pipeline.run_demo_a(_sample(), Brief(topic="x", region="北京"),
                              run_dir=str(tmp_path), url_opener=lambda u, t: 200)
    assert res.final_status == "awaiting_human"
