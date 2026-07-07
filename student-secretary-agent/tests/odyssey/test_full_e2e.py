"""P2-E2E: real Hermes Kanban roundtrip + kill->resume via HermesKanbanAdapter.

Formalizes the V0-3 spike proof (campus/odyssey/spike_resume.py) behind the
KanbanPort adapter. Requires hermes-agent installed; skipped otherwise.
"""
import os

import pytest

pytest.importorskip("hermes_cli")  # skip cleanly when Hermes is absent

from campus.runtime.hermes_kanban import HermesKanbanAdapter

os.environ.setdefault("HERMES_KANBAN_CRASH_GRACE_SECONDS", "0")
BOARD = "campus-phase2-e2e"


def _dead_stand_in_pid(kb):
    from hermes_cli import kanban_db
    for cand in (9999999, 8888888, 7777777, 6666666, 5555555):
        try:
            if not kanban_db._pid_alive(cand):
                return cand
        except Exception:
            continue
    pytest.skip("no dead stand-in pid found on this host")


def _runid(task):
    if isinstance(task, dict):
        return task.get("current_run_id")
    return getattr(task, "current_run_id", None)


def test_hermes_roundtrip_and_kill_resume():
    adapter = HermesKanbanAdapter(board=BOARD)
    conn = adapter.conn
    tid = adapter.create_task(
        title="phase2 e2e kill-resume", assignee="default",
        body="crash -> auto-reclaim -> respawn -> done")
    assert tid
    dead = _dead_stand_in_pid(adapter)
    state = {"n": 0}

    def spawn(task, ws, board):
        state["n"] += 1
        if state["n"] == 1:
            return dead                          # crashes (dead worker pid)
        adapter.complete_task(
            task.id, summary="resumed after crash",
            metadata={"proof": "phase2 e2e kill->resume"},
            expected_run_id=_runid(task))
        return None

    adapter.dispatch_once(spawn, failure_limit=5)      # tick1: spawn dead worker
    t = adapter.get_task(tid)
    assert t.status == "running", f"expected running after tick1, got {t.status!r}"

    adapter.dispatch_once(spawn, failure_limit=5)      # tick2: reclaim -> respawn -> done
    t = adapter.get_task(tid)
    assert t.status == "done", f"expected done after tick2, got {t.status!r}"

    runs = conn.execute(
        "SELECT outcome FROM task_runs WHERE task_id=? ORDER BY id", (tid,)
    ).fetchall()
    outcomes = [r[0] for r in runs]
    assert len(runs) >= 2, outcomes
    assert "crashed" in outcomes and "completed" in outcomes, outcomes

    kinds = [k[0] for k in conn.execute(
        "SELECT kind FROM task_events WHERE task_id=? ORDER BY id", (tid,)
    ).fetchall()]
    assert "crashed" in kinds and "completed" in kinds, kinds
