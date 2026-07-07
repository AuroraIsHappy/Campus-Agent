"""P2-S1/S2/S3/S4 + adversarial debate: supervisor four gates + run_debate."""
import pytest

from campus.odyssey.orchestrator import CostTracker, Orchestrator, TurnOutcome
from campus.odyssey.supervisor import (
    DEBATE_ESCALATED, DEBATE_FORCED, DEBATE_PASS, Supervisor,
)
from campus.runtime.in_memory import InMemoryKanban
from campus.runtime.ports import (
    APPROVE, AWAITING_HUMAN, CostLimitExceeded, ProtocolViolationError, REJECT,
)


def _approve(profile, task):
    return TurnOutcome(summary="ok", metadata={"verdict": APPROVE}, tokens=5)


# --- P2-S3 dialog protocol ---------------------------------------------------
def test_handoff_ok():
    s = Supervisor(InMemoryKanban("k"))
    assert s.validate_handoff("summary", {"verdict": APPROVE}, is_gate=True) is True


def test_handoff_missing_summary():
    s = Supervisor(InMemoryKanban("k"))
    with pytest.raises(ProtocolViolationError):
        s.validate_handoff("", {"verdict": APPROVE})


def test_handoff_none_summary():
    s = Supervisor(InMemoryKanban("k"))
    with pytest.raises(ProtocolViolationError):
        s.validate_handoff(None, {})


def test_handoff_gate_missing_verdict():
    s = Supervisor(InMemoryKanban("k"))
    with pytest.raises(ProtocolViolationError):
        s.validate_handoff("sum", {}, is_gate=True)


# --- P2-S1 round limit -------------------------------------------------------
def test_round_limit_under():
    s = Supervisor(InMemoryKanban("k"), max_rounds=3)
    assert s.enforce_round_limit("d1", 3) is False


def test_round_limit_over():
    s = Supervisor(InMemoryKanban("k"), max_rounds=3)
    assert s.enforce_round_limit("d1", 4) is True


# --- P2-S2 deadlock / idle ---------------------------------------------------
def test_deadlock_only_after_idle_rounds():
    s = Supervisor(InMemoryKanban("k"), idle_rounds=2)
    assert s.detect_deadlock(0) is False   # streak 1
    assert s.detect_deadlock(0) is True    # streak 2


def test_deadlock_resets_on_progress():
    s = Supervisor(InMemoryKanban("k"), idle_rounds=2)
    s.detect_deadlock(0)
    assert s.detect_deadlock(1) is False   # progress resets
    assert s.detect_deadlock(0) is False   # streak 1
    assert s.detect_deadlock(0) is True    # streak 2


# --- P2-S4 cost gate ---------------------------------------------------------
def test_cost_gate_under():
    cost = CostTracker()
    cost.add("t1", 50)
    s = Supervisor(InMemoryKanban("k"), cost_limit_per_task=100, cost=cost)
    assert s.enforce_cost("t1") is False


def test_cost_gate_over():
    cost = CostTracker()
    cost.add("t1", 150)
    s = Supervisor(InMemoryKanban("k"), cost_limit_per_task=100, cost=cost)
    with pytest.raises(CostLimitExceeded):
        s.enforce_cost("t1")


def test_cost_gate_disabled_when_no_tracker():
    s = Supervisor(InMemoryKanban("k"))   # no cost / no limit
    assert s.enforce_cost("t1") is False


# --- step integration --------------------------------------------------------
def test_step_records_completion_ok():
    kb = InMemoryKanban("s")
    orch = Orchestrator(kb)
    s = Supervisor(kb)
    tid = orch.create_task("planner", title="t")
    rep = s.step(orch.make_profile_spawn_fn(None, _approve))
    assert tid in rep.new_completions
    assert rep.ok


def test_step_flags_protocol_violation():
    kb = InMemoryKanban("v")
    orch = Orchestrator(kb)
    s = Supervisor(kb)
    tid = orch.create_task("planner", title="t")

    def no_summary(task, ws, board):
        kb.complete_task(task.id, metadata={"verdict": APPROVE})  # missing summary
        return None

    rep = s.step(no_summary)
    assert tid in rep.violations


def test_step_cost_breach_escalates():
    kb = InMemoryKanban("c")
    orch = Orchestrator(kb)
    cost = CostTracker()
    s = Supervisor(kb, cost_limit_per_task=1, cost=cost)   # _approve spends 5 > 1
    tid = orch.create_task("planner", title="t")
    rep = s.step(orch.make_profile_spawn_fn(None, _approve, cost=cost))
    assert tid in rep.cost_breaches
    assert tid in rep.escalations
    assert kb.get_task(tid).status == AWAITING_HUMAN


# --- run_debate (P2-D2 + S1 + S2) -------------------------------------------
def _seed_done_upstream(orch, kb, role="writer", title="draft"):
    uid = orch.create_task(role, title=title)
    orch.dispatch_once(lambda t, w, b: kb.complete_task(t.id, summary=title) or None)
    return uid


def test_debate_approve_passes():
    kb = InMemoryKanban("d1")
    orch = Orchestrator(kb)
    s = Supervisor(kb, max_rounds=3, idle_rounds=3)
    uid = _seed_done_upstream(orch, kb)

    def approve(task, ws, board):
        kb.complete_task(task.id, summary="reviewed", metadata={"verdict": APPROVE})
        return None

    res = s.run_debate(orch, approve, uid, "reviewer")
    assert res.outcome == DEBATE_PASS
    assert res.rounds == 1


def test_debate_reject_loops_to_force_pass():
    kb = InMemoryKanban("d2")
    orch = Orchestrator(kb)
    s = Supervisor(kb, max_rounds=2, idle_rounds=9)
    uid = _seed_done_upstream(orch, kb)

    def reject(task, ws, board):
        kb.complete_task(task.id, summary="rejected", metadata={"verdict": REJECT})
        return None

    res = s.run_debate(orch, reject, uid, "reviewer")
    assert res.outcome == DEBATE_FORCED
    g = kb.get_task(res.gate_task_id)
    assert g is not None and g.metadata.get("verdict_forced") is True


def test_debate_deadlock_escalates():
    kb = InMemoryKanban("d3")
    orch = Orchestrator(kb)
    s = Supervisor(kb, max_rounds=5, idle_rounds=2)
    uid = _seed_done_upstream(orch, kb)

    def external_never_completes(task, ws, board):
        return 12345   # live external worker that never calls complete_task

    res = s.run_debate(orch, external_never_completes, uid, "reviewer")
    assert res.outcome == DEBATE_ESCALATED
    assert kb.get_task(uid).status == AWAITING_HUMAN
