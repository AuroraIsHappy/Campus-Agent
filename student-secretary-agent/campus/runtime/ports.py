"""L2 Odyssey runtime ports (architecture §C4②): Campus code depends only on
``KanbanPort``, never on Hermes internals. Two implementations live beside this
file: ``InMemoryKanban`` (tests, no Hermes) and ``HermesKanbanAdapter`` (runtime,
wraps ``hermes_cli.kanban_db``).

Pure data models + a structural Protocol + the exceptions the gates raise.
No third-party imports; importable with plain Python (unit tests need no Hermes).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional, Protocol, runtime_checkable

__all__ = [
    # statuses
    "READY", "RUNNING", "DONE", "BLOCKED", "AWAITING_HUMAN", "FAILED",
    # verdicts
    "APPROVE", "REJECT", "PENDING",
    # models
    "Task", "DispatchBuckets", "Verdict",
    # port + errors
    "KanbanPort", "SpawnFn",
    "OdysseyError", "CyclicDAGError", "MissingParentError",
    "ProtocolViolationError", "CostLimitExceeded",
]

# --- task statuses (strings interop with Hermes kanban) ----------------------
READY = "ready"
RUNNING = "running"
DONE = "done"
BLOCKED = "blocked"               # DAG: waiting on parents
AWAITING_HUMAN = "awaiting_human"  # supervisor escalation
FAILED = "failed"

# --- verdicts (live in Task.metadata['verdict']) -----------------------------
APPROVE = "approve"
REJECT = "reject"
PENDING = "pending"

# handoff key the dialog-protocol gate enforces (architecture §4.2 / S-SUPERVISOR)
VERDICT_KEY = "verdict"
SUMMARY_KEY = "summary"


@dataclass
class Task:
    """A Kanban task row. Mutable: the kanban implementation owns status transitions."""
    id: str
    title: str
    body: Optional[str] = None
    assignee: Optional[str] = None          # role / profile name
    status: str = READY
    parents: tuple[str, ...] = ()
    priority: int = 0
    goal_mode: bool = False
    skills: tuple[str, ...] = ()
    max_retries: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    summary: Optional[str] = None
    current_run_id: Optional[int] = None
    worker_pid: Optional[int] = None
    board: Optional[str] = None

    @property
    def verdict(self) -> str:
        return self.metadata.get(VERDICT_KEY, PENDING)

    @property
    def is_terminal(self) -> bool:
        return self.status in (DONE, AWAITING_HUMAN, FAILED)


@dataclass
class DispatchBuckets:
    """Per-tick dispatch outcome (mirrors Hermes DispatchResult fields)."""
    spawned: int = 0
    reclaimed: int = 0
    crashed: int = 0
    stale: int = 0
    promoted: int = 0
    skipped_unassigned: int = 0
    auto_assigned_default: int = 0
    skipped_nonspawnable: int = 0
    skipped_per_profile_capped: int = 0
    auto_blocked: int = 0
    timed_out: int = 0
    respawn_guarded: int = 0
    rate_limited: int = 0
    skipped_locked: int = 0
    spawned_ids: list[str] = field(default_factory=list)

    @property
    def did_work(self) -> bool:
        """True if this tick changed anything the supervisor should react to."""
        return bool(self.spawned or self.reclaimed or self.crashed or self.stale)


@dataclass
class Verdict:
    """An adversarial-pair decision (Planner↔Critic, Writer↔Reviewer)."""
    verdict: str          # APPROVE / REJECT / PENDING
    reason: str = ""
    role: Optional[str] = None
    round: int = 0

    def to_meta(self) -> dict[str, Any]:
        return {VERDICT_KEY: self.verdict, "reason": self.reason,
                "verdict_by": self.role, "verdict_round": self.round}


# spawn_fn(task, workspace_path, board) -> pid | None  (None = inline self-completing)
SpawnFn = Callable[[Task, Optional[str], Optional[str]], Optional[int]]


# --- errors ------------------------------------------------------------------
class OdysseyError(Exception):
    """Base for Odyssey-level failures."""


class CyclicDAGError(OdysseyError):
    """parents form a cycle (P2-D1)."""


class MissingParentError(OdysseyError):
    """a parent id does not exist (P2-D1)."""


class ProtocolViolationError(OdysseyError):
    """handoff did not use kanban_complete(summary, metadata) (P2-S3)."""


class CostLimitExceeded(OdysseyError):
    """single-task token spend crossed the cost gate (P2-S4)."""


@runtime_checkable
class KanbanPort(Protocol):
    """The thin surface Campus orchestrator/supervisor depend on.

    ``assignee`` is the role/profile name; ``parents`` encode DAG deps; the
    adversarial verdict travels in ``metadata['verdict']`` of completed tasks.
    """

    board: Optional[str]

    def create_task(self, *, title: str, body: Optional[str] = None,
                    assignee: Optional[str] = None,
                    parents: Iterable[str] = (), priority: int = 0,
                    goal_mode: bool = False, skills: Iterable[str] = (),
                    max_retries: Optional[int] = None,
                    initial_status: Optional[str] = None) -> str: ...

    def dispatch_once(self, spawn_fn: Optional[SpawnFn] = None, *,
                      failure_limit: int = 2, max_spawn: Optional[int] = None,
                      default_assignee: Optional[str] = None) -> DispatchBuckets: ...

    def complete_task(self, task_id: str, *, summary: Optional[str] = None,
                      metadata: Optional[dict[str, Any]] = None,
                      expected_run_id: Optional[int] = None) -> bool: ...

    def detect_crashed_workers(self) -> list[str]: ...

    def recompute_ready(self) -> int: ...

    def get_task(self, task_id: str) -> Optional[Task]: ...

    def list_children(self, parent_id: str) -> list[Task]: ...

    def all_tasks(self) -> list[Task]: ...
