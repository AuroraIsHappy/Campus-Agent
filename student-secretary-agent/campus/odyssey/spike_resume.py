# V0-3 spike: Hermes Kanban crash -> auto-reclaim -> resume -> done (fork-free).
#   tick1: spawn_fn returns a known-DEAD pid (stand-in for a crashed worker);
#          dispatcher records it as worker_pid (run R1 = running).
#   tick2: detect_crashed_workers (crash grace=0 via env) sees _pid_alive=False
#          -> reclaim R1=crashed, task->ready; then spawn loop respawns (R2)
#          and spawn_fn completes it (R2=completed). All in one tick.
# Evidence: final status=done; task_runs>=2 (crashed+completed); 'crashed' event.
# Run: student-secretary-agent/.venv/Scripts/python.exe -m campus.odyssey.spike_resume
from __future__ import annotations
import os
import sys
import traceback

os.environ.setdefault("HERMES_KANBAN_CRASH_GRACE_SECONDS", "0")


def _tid(task):
    if isinstance(task, dict):
        return task.get("id") or task.get("task_id")
    return getattr(task, "id", None) or getattr(task, "task_id", None)


def _runid(task):
    if isinstance(task, dict):
        return task.get("current_run_id")
    return getattr(task, "current_run_id", None)


def _dead_stand_in_pid(kb):
    for cand in (9999999, 8888888, 7777777, 6666666, 5555555):
        try:
            if not kb._pid_alive(cand):
                return cand
        except Exception:
            continue
    raise RuntimeError("could not find a dead stand-in pid on this host")
def main() -> int:
    from hermes_cli import kanban_db as kb

    BOARD = "campus-spike-resume"
    print(f"[spike-resume] board={BOARD!r}")
    conn = kb.connect(board=BOARD)

    kb.create_task(
        conn,
        title="resume spike V0-3",
        assignee="default",
        body="crash -> auto-reclaim -> respawn -> done",
        workspace_kind="scratch",
    )
    tid = conn.execute(
        "SELECT id FROM tasks WHERE title=? ORDER BY rowid DESC LIMIT 1",
        ("resume spike V0-3",),
    ).fetchone()[0]
    print(f"[spike-resume] created task_id={tid!r}")

    holder = {}

    def spawn_crash(task, workspace_path, board):
        claimed_id = _tid(task)
        run1 = _runid(task)
        pid = _dead_stand_in_pid(kb)
        holder["pid"] = pid
        holder["run1"] = run1
        print(f"[spike-resume] tick1: dead stand-in worker_pid={pid} task={claimed_id} run={run1}")
        return pid

    res1 = kb.dispatch_once(conn, spawn_fn=spawn_crash, board=BOARD, failure_limit=5)
    print(f"[spike-resume] tick1 result spawned={res1.spawned}")

    r1 = conn.execute(
        "SELECT status, worker_pid, current_run_id FROM tasks WHERE id=?", (tid,)
    ).fetchone()
    print(f"[spike-resume] after tick1: status={r1[0]!r} worker_pid={r1[1]!r} run={r1[2]!r}")
    assert r1[0] == "running", f"expected running after tick1, got {r1[0]!r}"
    assert r1[1] == holder["pid"], f"worker_pid {r1[1]!r} != stand-in"
    def spawn_complete(task, workspace_path, board):
        claimed_id = _tid(task)
        run2 = _runid(task)
        print(f"[spike-resume] tick2: respawned task={claimed_id} run={run2}; completing")
        kb.complete_task(
            conn,
            claimed_id,
            summary="resumed after crash",
            metadata={"proof": "V0-3 crash->resume", "origin": "spike_resume"},
            expected_run_id=run2,
        )
        return None

    res2 = kb.dispatch_once(conn, spawn_fn=spawn_complete, board=BOARD, failure_limit=5)
    print(f"[spike-resume] tick2 reclaimed={res2.reclaimed} stale={res2.stale} crashed={res2.crashed} spawned={res2.spawned}")

    trow = conn.execute("SELECT status FROM tasks WHERE id=?", (tid,)).fetchone()
    runs = conn.execute(
        "SELECT id, status, outcome FROM task_runs WHERE task_id=? ORDER BY id", (tid,)
    ).fetchall()
    kinds = conn.execute(
        "SELECT kind FROM task_events WHERE task_id=? ORDER BY id", (tid,)
    ).fetchall()
    final_status = trow[0] if trow else None
    run_outcomes = [r[2] for r in runs]
    event_kinds = [k[0] for k in kinds]
    print(f"[verify] final task status = {final_status!r}")
    print(f"[verify] task_runs ({len(runs)}): {[tuple(r) for r in runs]}")
    print(f"[verify] run outcomes      = {run_outcomes}")
    print(f"[verify] event kinds       = {event_kinds}")
    ok = (
        final_status == "done"
        and len(runs) >= 2
        and "crashed" in run_outcomes
        and "completed" in run_outcomes
        and "crashed" in event_kinds
    )
    print("[spike-resume][PASS] crash -> auto-reclaim -> resume -> done" if ok
          else "[spike-resume][FAIL] see above")
    return 0 if ok else 5


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
