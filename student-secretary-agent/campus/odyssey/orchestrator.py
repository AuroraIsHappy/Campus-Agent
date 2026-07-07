"""L2 Odyssey orchestrator (architecture §4.1, IMPLEMENT Phase 2).

Thin layer over ``KanbanPort``:
  * ``create_task(assignee, parents, goal_mode=True)`` validates parents then delegates;
  * ``dispatch_once(spawn_fn)`` drives one kanban tick;
  * ``make_profile_spawn_fn(loader, turn_fn)`` is the seam that turns a task row into
    "spawn an agent bound to the role's profile, run one goal turn, hand off via
    kanban_complete(summary, metadata)".

The actual LLM turn is injected as ``turn_fn`` — a fake in unit tests, a Hermes
delegate/oneshot call at runtime (out of scope for Phase 2; seam only).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from campus.orchestrator import dag as dag_mod
from campus.runtime.ports import (
    DispatchBuckets, KanbanPort, MissingParentError, SpawnFn, Task,
)

__all__ = ["Orchestrator", "TurnOutcome", "CostTracker"]


@dataclass
class TurnOutcome:
    """What a role turn produces: a handoff summary + metadata + token spend."""
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)
    tokens: int = 0


class CostTracker:
    """Per-task token accumulator (feeds the supervisor cost gate)."""

    def __init__(self) -> None:
        self._spent: dict[str, int] = {}

    def add(self, task_id: str, tokens: int) -> None:
        self._spent[task_id] = self._spent.get(task_id, 0) + int(tokens)

    def spent(self, task_id: str) -> int:
        return self._spent.get(task_id, 0)

    def total(self) -> int:
        return sum(self._spent.values())


class Orchestrator:
    def __init__(self, kanban: KanbanPort) -> None:
        self.kanban = kanban

    def create_task(self, assignee: Optional[str], *, title: str,
                    body: Optional[str] = None, parents: tuple[str, ...] = (),
                    goal_mode: bool = True, priority: int = 0,
                    skills: tuple[str, ...] = (),
                    max_retries: Optional[int] = None) -> str:
        parents_t = tuple(parents)
        existing = {t.id for t in self.kanban.all_tasks()}
        for p in parents_t:
            if p not in existing:
                raise MissingParentError(f"parent {p!r} does not exist")
        return self.kanban.create_task(
            title=title, body=body, assignee=assignee, parents=parents_t,
            priority=priority, goal_mode=goal_mode, skills=skills,
            max_retries=max_retries)

    def dispatch_once(self, spawn_fn: Optional[SpawnFn] = None, **kw) -> DispatchBuckets:
        return self.kanban.dispatch_once(spawn_fn, **kw)

    def run_to_completion(self, spawn_fn: Optional[SpawnFn] = None, *,
                          max_ticks: int = 50, **kw) -> int:
        """Drive dispatch ticks until a tick does no real work. Returns ticks used."""
        ticks = 0
        for _ in range(max_ticks):
            ticks += 1
            b = self.kanban.dispatch_once(spawn_fn, **kw)
            crashed = self.kanban.detect_crashed_workers()
            if not b.did_work and not crashed:
                break
        return ticks

    def make_profile_spawn_fn(self, loader=None,
                              turn_fn: Optional[Callable[[dict, Task], TurnOutcome]] = None,
                              cost: Optional[CostTracker] = None) -> SpawnFn:
        """Build a spawn_fn that binds each task to its role profile and runs one turn."""
        def spawn(task: Task, workspace_path, board) -> None:
            role = task.assignee
            profile = loader.get(role) if loader is not None else {"role": role}
            if turn_fn is None:
                raise RuntimeError("turn_fn not configured")
            out = turn_fn(profile, task)
            if cost is not None and out.tokens:
                cost.add(task.id, out.tokens)
            self.kanban.complete_task(
                task.id, summary=out.summary, metadata=out.metadata,
                expected_run_id=task.current_run_id)
            return None
        return spawn
