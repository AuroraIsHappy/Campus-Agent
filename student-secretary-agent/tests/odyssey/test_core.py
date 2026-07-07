"""P2-O1/O2 + DAG/adversarial: orchestrator roundtrip, kill->resume, DAG, cost."""
import pytest

from campus.orchestrator.dag import create_adversarial_pair
from campus.odyssey.orchestrator import CostTracker, Orchestrator, TurnOutcome
from campus.runtime.in_memory import InMemoryKanban
from campus.runtime.ports import APPROVE, BLOCKED, DONE, READY, RUNNING, MissingParentError


def _approve(profile, task):
    return TurnOutcome(summary=f"done by {task.assignee}",
                       metadata={"verdict": APPROVE}, tokens=10)


def test_roundtrip_create_dispatch_complete():
    # P2-O1: orchestrator create -> dispatch(spawn_fn) -> complete; status DONE + verdict.
    kb = InMemoryKanban("rt")
    orch = Orchestrator(kb)
    tid = orch.create_task("planner", title="plan something", goal_mode=True)
    spawn = orch.make_profile_spawn_fn(loader=None, turn_fn=_approve)
    orch.dispatch_once(spawn)
    t = kb.get_task(tid)
    assert t.status == DONE
    assert t.verdict == APPROVE
    assert t.summary == "done by planner"


def test_kill_then_resume():
    # P2-O2: dead-pid worker -> reclaim -> respawn -> done (mirrors V0-3 spike).
    kb = InMemoryKanban("resume")
    orch = Orchestrator(kb)
    DEAD = 7654321
    state = {"n": 0}

    def crash_then_done(task, ws, board):
        state["n"] += 1
        if state["n"] == 1:
            return DEAD                      # crashes
        kb.complete_task(task.id, summary="resumed", metadata={"verdict": APPROVE})
        return None

    tid = orch.create_task("default", title="r")
    orch.dispatch_once(crash_then_done, failure_limit=5)
    t = kb.get_task(tid)
    assert t.status == RUNNING and t.worker_pid == DEAD
    kb.mark_pid_dead(DEAD)
    orch.dispatch_once(crash_then_done, failure_limit=5)
    t = kb.get_task(tid)
    assert t.status == DONE
    runs = kb.runs_for(tid)
    outcomes = [r.outcome for r in runs]
    assert len(runs) >= 2
    assert "crashed" in outcomes and "completed" in outcomes
    assert "crashed" in kb.events_for(tid)


def test_dag_child_blocked_until_parent_done():
    kb = InMemoryKanban("dag")
    orch = Orchestrator(kb)
    pid = orch.create_task("researcher", title="parent")
    cid = orch.create_task("writer", title="child", parents=(pid,))
    assert kb.get_task(cid).status == BLOCKED
    orch.dispatch_once(lambda t, ws, bd: kb.complete_task(t.id, summary="p") or None)
    assert kb.get_task(pid).status == DONE
    assert kb.get_task(cid).status == READY   # unblocked


def test_missing_parent_raises():
    kb = InMemoryKanban("mp")
    orch = Orchestrator(kb)
    with pytest.raises(MissingParentError):
        orch.create_task("writer", title="orphan", parents=("t_nope",))


def test_adversarial_pair_gate_blocked_then_runs():
    # P2-D2 (lite): Writer->Reviewer pair; reviewer BLOCKED until writer done.
    kb = InMemoryKanban("adv")
    orch = Orchestrator(kb)
    uid, gid = create_adversarial_pair(
        orch, upstream_role="writer", gate_role="reviewer",
        upstream_title="draft", gate_title="review", goal="g")
    assert kb.get_task(gid).status == BLOCKED

    def turn(task, ws, board):
        kb.complete_task(task.id, summary=task.title, metadata={"verdict": APPROVE})
        return None

    orch.dispatch_once(turn)                  # writer runs -> done -> reviewer unblocks
    assert kb.get_task(uid).status == DONE
    assert kb.get_task(gid).status == READY
    orch.dispatch_once(turn)                  # reviewer runs -> done
    assert kb.get_task(gid).status == DONE
    assert kb.get_task(gid).verdict == APPROVE


def test_spawn_fn_records_cost():
    kb = InMemoryKanban("cost")
    orch = Orchestrator(kb)
    cost = CostTracker()
    spawn = orch.make_profile_spawn_fn(loader=None, turn_fn=_approve, cost=cost)
    tid = orch.create_task("planner", title="t")
    orch.dispatch_once(spawn)
    assert cost.spent(tid) == 10
    assert cost.total() == 10


def test_run_to_completion_drives_children():
    kb = InMemoryKanban("chain")
    orch = Orchestrator(kb)
    a = orch.create_task("researcher", title="A")
    b = orch.create_task("writer", title="B", parents=(a,))
    spawn = orch.make_profile_spawn_fn(loader=None, turn_fn=_approve)
    orch.run_to_completion(spawn)
    assert kb.get_task(a).status == DONE
    assert kb.get_task(b).status == DONE
