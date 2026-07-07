"""InMemoryKanban: a faithful in-process fake of Hermes Kanban for unit tests.

Implements ``KanbanPort`` with the semantics Phase 2 relies on:
  * DAG parent-dependency readiness (child BLOCKED until all parents DONE),
  * the spawn_fn seam (returns pid = external worker; None = inline self-complete),
  * crash -> detect -> reclaim -> respawn (mirrors the V0-3 spike proof), so the
    kill->resume unit test reproduces the real Hermes evidence (task_runs>=2 with
    crashed+completed, final status done).

No file IO, no Hermes import, no network. Plain Python.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional

from campus.runtime.ports import (
    AWAITING_HUMAN, BLOCKED, DONE, FAILED, PENDING, READY, RUNNING,
    VERDICT_KEY, DispatchBuckets, SpawnFn, Task,
)

__all__ = ["InMemoryKanban", "Run", "KanbanEvent"]


def _default_pid_alive(dead: set[int]) -> Callable[[Optional[int]], bool]:
    def alive(pid: Optional[int]) -> bool:
        return pid is not None and pid not in dead
    return alive


@dataclass
class Run:
    id: int
    task_id: str
    status: str = RUNNING        # running / done / crashed
    outcome: Optional[str] = None  # completed / crashed


@dataclass
class KanbanEvent:
    task_id: str
    kind: str


class InMemoryKanban:
    """KanbanPort impl backed by plain dicts. Construct with a board name."""

    def __init__(self, board: str = "campus-test",
                 pid_alive: Optional[Callable[[Optional[int]], bool]] = None) -> None:
        self.board: Optional[str] = board
        self._tasks: dict[str, Task] = {}
        self._runs: list[Run] = []
        self._events: list[KanbanEvent] = []
        self._dead_pids: set[int] = set()
        self._pid_alive = pid_alive or _default_pid_alive(self._dead_pids)
        self._seq = 0
        self._run_seq = 0
        self._crash_counts: dict[str, int] = {}

    # --- id helpers --------------------------------------------------------
    def _new_id(self) -> str:
        self._seq += 1
        return f"t_{self._seq:08x}"

    def _new_run(self, task_id: str) -> Run:
        self._run_seq += 1
        run = Run(id=self._run_seq, task_id=task_id)
        self._runs.append(run)
        return run

    def _emit(self, task_id: str, kind: str) -> None:
        self._events.append(KanbanEvent(task_id, kind))

    # --- public port surface ----------------------------------------------
    def create_task(self, *, title: str, body: Optional[str] = None,
                    assignee: Optional[str] = None,
                    parents: Iterable[str] = (), priority: int = 0,
                    goal_mode: bool = False, skills: Iterable[str] = (),
                    max_retries: Optional[int] = None,
                    initial_status: Optional[str] = None) -> str:
        parents_t = tuple(parents)
        for p in parents_t:
            if p not in self._tasks:
                # orchestrator validates first; defensive guard here too
                raise KeyError(f"unknown parent task: {p!r}")
        tid = self._new_id()
        status = initial_status
        if status is None:
            status = READY if self._parents_done(parents_t) else BLOCKED
        t = Task(id=tid, title=title, body=body, assignee=assignee, status=status,
                 parents=parents_t, priority=priority, goal_mode=goal_mode,
                 skills=tuple(skills), max_retries=max_retries, board=self.board)
        self._tasks[tid] = t
        self._emit(tid, "created")
        return tid

    def recompute_ready(self) -> int:
        promoted = 0
        for t in self._tasks.values():
            if t.status == BLOCKED and self._parents_done(t.parents):
                t.status = READY
                promoted += 1
                self._emit(t.id, "promoted")
        return promoted

    def _parents_done(self, parents: tuple[str, ...]) -> bool:
        return all(self._tasks[p].status == DONE for p in parents if p in self._tasks)

    def _ready_queue(self) -> list[Task]:
        # priority desc, then creation order
        return sorted((t for t in self._tasks.values() if t.status == READY),
                      key=lambda x: (-x.priority, x.id))

    def dispatch_once(self, spawn_fn: Optional[SpawnFn] = None, *,
                      failure_limit: int = 2, max_spawn: Optional[int] = None,
                      default_assignee: Optional[str] = None) -> DispatchBuckets:
        b = DispatchBuckets()
        # 1) reclaim crashed workers first (Hermes does detect -> reclaim -> respawn)
        for tid in self.detect_crashed_workers():
            t = self._tasks[tid]
            attempts = self._crash_counts.get(tid, 0) + 1
            self._crash_counts[tid] = attempts
            if attempts > failure_limit:
                t.status = FAILED
                self._emit(tid, "auto_blocked")
                b.auto_blocked += 1
                continue
            self._end_run(tid, outcome="crashed")
            t.status = READY
            t.worker_pid = None
            self._emit(tid, "crashed")
            b.crashed += 1
        self.recompute_ready()
        if spawn_fn is None:
            return b
        # 2) spawn ready tasks
        queue = self._ready_queue()
        if max_spawn is not None:
            queue = queue[:max_spawn]
        for t in queue:
            if t.assignee is None:
                if default_assignee:
                    t.assignee = default_assignee
                    b.auto_assigned_default += 1
                else:
                    b.skipped_unassigned += 1
                    continue
            t.status = RUNNING
            run = self._new_run(t.id)
            t.current_run_id = run.id
            self._emit(t.id, "claimed")
            self._emit(t.id, "spawned")
            pid = spawn_fn(t, self._workspace(t), self.board)
            if pid is not None:
                t.worker_pid = pid
            # pid None => spawn_fn self-completed via complete_task (inline)
            b.spawned += 1
            b.spawned_ids.append(t.id)
        return b

    def complete_task(self, task_id: str, *, summary: Optional[str] = None,
                      metadata: Optional[dict[str, Any]] = None,
                      expected_run_id: Optional[int] = None) -> bool:
        t = self._tasks.get(task_id)
        if t is None:
            return False
        if t.status == DONE:
            return True
        t.status = DONE
        if summary is not None:
            t.summary = summary
        if metadata:
            t.metadata.update(metadata)
        self._end_run(task_id, outcome="completed")
        self._emit(task_id, "completed")
        self.recompute_ready()
        return True

    def _end_run(self, task_id: str, outcome: str) -> None:
        t = self._tasks.get(task_id)
        rid = t.current_run_id if t else None
        if rid is None:
            return
        for r in reversed(self._runs):
            if r.id == rid:
                r.status = "done" if outcome == "completed" else "crashed"
                r.outcome = outcome
                break
        t.current_run_id = None

    def detect_crashed_workers(self) -> list[str]:
        out = []
        for t in self._tasks.values():
            if t.status == RUNNING and not self._pid_alive(t.worker_pid):
                out.append(t.id)
        return out

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_children(self, parent_id: str) -> list[Task]:
        return [t for t in self._tasks.values() if parent_id in t.parents]

    def all_tasks(self) -> list[Task]:
        return list(self._tasks.values())

    # --- test helpers (not in the port) -----------------------------------
    def _workspace(self, t: Task) -> Optional[str]:
        return f"<in-memory>/workspaces/{t.id}"

    def mark_pid_dead(self, pid: int) -> None:
        """Register a stand-in pid as dead (V0-3 spike technique)."""
        self._dead_pids.add(pid)

    def simulate_crash(self, task_id: str) -> None:
        """Force a running task's worker to be considered dead (next tick reclaims)."""
        t = self._tasks.get(task_id)
        if t and t.status == RUNNING and t.worker_pid is not None:
            self.mark_pid_dead(t.worker_pid)

    def escalate(self, task_id: str, reason: str = "") -> None:
        """Supervisor escalation to awaiting_human."""
        t = self._tasks.get(task_id)
        if t is None:
            return
        t.status = AWAITING_HUMAN
        t.metadata["escalation"] = reason
        self._emit(task_id, "escalated")

    def runs_for(self, task_id: str) -> list[Run]:
        return [r for r in self._runs if r.task_id == task_id]

    def events_for(self, task_id: str) -> list[str]:
        return [e.kind for e in self._events if e.task_id == task_id]
