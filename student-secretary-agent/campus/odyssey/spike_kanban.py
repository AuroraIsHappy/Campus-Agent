"""V0-2 spike: Hermes Kanban roundtrip.

create_task -> dispatch_once(inline spawn_fn) -> complete_task -> verify row.
Goal: prove the Kanban engine works end-to-end with an external orchestrator
driving it via dispatch_once(spawn_fn=...). No LLM, no fork.

Run (from repo root):
  student-secretary-agent/.venv/Scripts/python.exe \
      student-secretary-agent/campus/odyssey/spike_kanban.py
"""
from __future__ import annotations
import sys
import traceback


def _tid(task) -> str | None:
    if isinstance(task, dict):
        return task.get("id") or task.get("task_id")
    try:  # sqlite3.Row supports __getitem__
        return task["id"]
    except Exception:
        return getattr(task, "id", None) or getattr(task, "task_id", None)


def _field(task, name, default=None):
    if isinstance(task, dict):
        return task.get(name, default)
    try:
        return task[name]
    except Exception:
        return getattr(task, name, default)


def main() -> int:
    from hermes_cli.kanban_db import connect, create_task, dispatch_once, complete_task

    BOARD = "campus-spike"
    print(f"[spike] connecting to kanban board={BOARD!r}")
    conn = connect(board=BOARD)

    # 1) create a task with an assignee (so dispatch will spawn it)
    tid = create_task(
        conn,
        title="kanban spike V0-2",
        assignee="default",  # MUST be a real Hermes profile — "tester" doesn't exist → skipped_nonspawnable
        body="roundtrip proof: create -> dispatch -> complete",
        workspace_kind="scratch",
    )
    # some implementations return the row id; others return None and commit.
    if not tid:
        row = conn.execute(
            "SELECT id FROM tasks ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        tid = row[0] if row else None
    print(f"[spike] created task_id={tid!r}")
    if not tid:
        print("[spike][FAIL] could not resolve task id")
        return 2

    # 2) inline spawn_fn: does the "work" synchronously and completes the task.
    # Captures `conn` from the closure. Returns None (no external PID).
    def inline_spawn(task, workspace_path, board):
        claimed_id = _tid(task)
        run_id = _field(task, "current_run_id")
        assignee = _field(task, "assignee")
        print(f"[worker] claimed task={claimed_id} assignee={assignee} run={run_id} ws={workspace_path}")
        complete_task(
            conn,
            claimed_id,
            summary="spike complete",
            metadata={"proof": "kanban roundtrip ok", "origin": "spike_kanban"},
            expected_run_id=run_id,
        )
        print(f"[worker] completed task={claimed_id}")
        return None  # no external worker process

    # 3) drive one dispatch tick
    print("[spike] dispatch_once ...")
    res = dispatch_once(conn, spawn_fn=inline_spawn, board=BOARD)
    print(f"[spike] dispatch result={res!r}")

    # 4) verify the task row
    row = conn.execute(
        "SELECT id, status, assignee, result FROM tasks WHERE id=?", (tid,)
    ).fetchone()
    print(f"[verify] row={tuple(row) if row else None}")

    if not row:
        print("[spike][FAIL] task row not found after dispatch")
        return 3
    status = row[1]
    result = row[3] or ""
    ok = status in ("done", "completed", "success", "ok") or "kanban roundtrip ok" in result
    print(f"[spike] status={status!r} ok={ok}")
    print("[spike][PASS] Kanban roundtrip works" if ok else "[spike][FAIL] see above")
    return 0 if ok else 4


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
