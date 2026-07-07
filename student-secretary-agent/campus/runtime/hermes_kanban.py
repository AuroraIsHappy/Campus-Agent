"""HermesKanbanAdapter: KanbanPort impl backed by the real Hermes Kanban engine.

Thin pass-through to ``hermes_cli.kanban_db`` (connect/create_task/dispatch_once/
complete_task/detect_crashed_workers). ``hermes_cli`` is imported lazily so the
unit-test environment (no Hermes installed) can still import this package; only
instantiation requires Hermes.

The board's ``sqlite3.Connection`` is exposed as ``self.conn`` so the e2e test can
run the same ``task_runs`` / ``task_events`` SQL the V0-3 spike used for evidence.
"""
from __future__ import annotations
from typing import Any, Iterable, Optional

from campus.runtime.ports import (
    DONE, DispatchBuckets, SpawnFn, Task,
)

__all__ = ["HermesKanbanAdapter"]


def _count(x: Any) -> int:
    """Hermes DispatchResult buckets are sometimes lists, sometimes ints."""
    if x is None:
        return 0
    if isinstance(x, (list, tuple, set)):
        return len(x)
    return int(x)


class HermesKanbanAdapter:
    def __init__(self, board: str = "campus", db_path: Optional[str] = None) -> None:
        from hermes_cli import kanban_db as k
        self._k = k
        self.board: Optional[str] = board
        self.conn = k.connect(db_path, board=board)

    # --- port surface ------------------------------------------------------
    def create_task(self, *, title: str, body: Optional[str] = None,
                    assignee: Optional[str] = None,
                    parents: Iterable[str] = (), priority: int = 0,
                    goal_mode: bool = False, skills: Iterable[str] = (),
                    max_retries: Optional[int] = None,
                    initial_status: Optional[str] = None) -> str:
        kwargs: dict[str, Any] = dict(
            title=title, body=body, assignee=assignee, parents=tuple(parents),
            priority=priority, goal_mode=goal_mode, skills=tuple(skills) or None,
            board=self.board,
        )
        if max_retries is not None:
            kwargs["max_retries"] = max_retries
        if initial_status is not None:
            kwargs["initial_status"] = initial_status
        return self._k.create_task(self.conn, **kwargs)

    def dispatch_once(self, spawn_fn: Optional[SpawnFn] = None, *,
                      failure_limit: int = 2, max_spawn: Optional[int] = None,
                      default_assignee: Optional[str] = None) -> DispatchBuckets:
        kwargs: dict[str, Any] = dict(failure_limit=failure_limit, board=self.board)
        if spawn_fn is not None:
            kwargs["spawn_fn"] = spawn_fn
        if max_spawn is not None:
            kwargs["max_spawn"] = max_spawn
        if default_assignee is not None:
            kwargs["default_assignee"] = default_assignee
        res = self._k.dispatch_once(self.conn, **kwargs)
        return self._convert(res)

    def complete_task(self, task_id: str, *, summary: Optional[str] = None,
                      metadata: Optional[dict[str, Any]] = None,
                      expected_run_id: Optional[int] = None) -> bool:
        kwargs: dict[str, Any] = {}
        if summary is not None:
            kwargs["summary"] = summary
        if metadata is not None:
            kwargs["metadata"] = metadata
        if expected_run_id is not None:
            kwargs["expected_run_id"] = expected_run_id
        return self._k.complete_task(self.conn, task_id, **kwargs)

    def detect_crashed_workers(self) -> list[str]:
        return self._k.detect_crashed_workers(self.conn)

    def recompute_ready(self) -> int:
        return self._k.recompute_ready(self.conn)

    # --- introspection (best-effort; e2e asserts via raw SQL on self.conn) -
    def _row_to_task(self, row) -> Task:
        keys = row.keys() if hasattr(row, "keys") else []
        def g(name, default=None):
            return row[name] if name in keys else default
        return Task(
            id=g("id"), title=g("title", "") or "", body=g("body"),
            assignee=g("assignee"), status=g("status", "ready"),
            priority=g("priority", 0) or 0, summary=g("summary"),
            current_run_id=g("current_run_id"), worker_pid=g("worker_pid"),
            board=self.board,
        )

    def get_task(self, task_id: str) -> Optional[Task]:
        row = self.conn.execute(
            "SELECT * FROM tasks WHERE id=?", (task_id,)
        ).fetchone()
        return self._row_to_task(row) if row else None

    def list_children(self, parent_id: str) -> list[Task]:
        out = []
        for row in self.conn.execute("SELECT * FROM tasks").fetchall():
            t = self._row_to_task(row)
            if parent_id in t.parents:
                out.append(t)
        return out

    def all_tasks(self) -> list[Task]:
        return [self._row_to_task(r) for r in
                self.conn.execute("SELECT * FROM tasks").fetchall()]

    # --- dispatch result conversion ---------------------------------------
    def _convert(self, res) -> DispatchBuckets:
        b = DispatchBuckets()
        for f in ("reclaimed", "promoted", "skipped_unassigned",
                  "auto_assigned_default", "skipped_nonspawnable",
                  "skipped_per_profile_capped", "crashed", "auto_blocked",
                  "timed_out", "stale", "respawn_guarded", "rate_limited",
                  "skipped_locked"):
            setattr(b, f, _count(getattr(res, f, None)))
        spawned = getattr(res, "spawned", None)
        b.spawned = _count(spawned)
        if isinstance(spawned, (list, tuple)):
            b.spawned_ids = [r[0] if isinstance(r, (list, tuple)) else r
                             for r in spawned]
        return b
