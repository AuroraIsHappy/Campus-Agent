"""L2 Supervisor (architecture §4.2 / S-SUPERVISOR, P2-S1..S4).

Hooks the dispatch tick and enforces four gates:
  * round-limit  (P2-S1): an adversarial debate exceeding ``max_rounds`` is force-passed
    and annotated (``metadata['verdict_forced']=True``);
  * deadlock/idle (P2-S2): ``idle_rounds`` consecutive ticks with no new completion
    escalate the task to ``awaiting_human``;
  * dialog protocol (P2-S3): every handoff must be ``kanban_complete(summary, metadata)``
    — a missing summary (or a gate task with no verdict) is a ProtocolViolationError;
  * cost gate (P2-S4): per-task token spend over ``cost_limit_per_task`` escalates.

Pure logic over ``KanbanPort``; the LLM turn is injected (fake in tests).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional

from campus.orchestrator.dag import VERDICT_PASS
from campus.runtime.ports import (
    APPROVE, AWAITING_HUMAN, DONE, PENDING, REJECT, VERDICT_KEY,
    CostLimitExceeded, KanbanPort, ProtocolViolationError, SpawnFn, Task,
)

__all__ = ["Supervisor", "SupervisorReport", "DebateResult",
           "DEBATE_PASS", "DEBATE_FORCED", "DEBATE_ESCALATED"]

DEBATE_PASS = "pass"
DEBATE_FORCED = "forced"
DEBATE_ESCALATED = "escalated"


@dataclass
class SupervisorReport:
    spawned: int = 0
    new_completions: list[str] = field(default_factory=list)
    forced_passes: list[str] = field(default_factory=list)
    escalations: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    cost_breaches: list[str] = field(default_factory=list)
    idle: bool = False

    @property
    def ok(self) -> bool:
        return not (self.violations or self.cost_breaches)


@dataclass
class DebateResult:
    outcome: str            # DEBATE_PASS / DEBATE_FORCED / DEBATE_ESCALATED
    rounds: int = 0
    gate_task_id: Optional[str] = None
    reason: str = ""


class Supervisor:
    def __init__(self, kanban: KanbanPort, *, max_rounds: int = 3,
                 idle_rounds: int = 2, cost_limit_per_task: Optional[int] = None,
                 cost=None) -> None:
        self.kanban = kanban
        self.max_rounds = max_rounds
        self.idle_rounds = idle_rounds
        self.cost_limit_per_task = cost_limit_per_task
        self.cost = cost
        self._rounds: dict[str, int] = {}
        self._done_ids: set[str] = set()
        self._idle_streak = 0

    # --- individual gates (each directly unit-testable) -------------------

    def validate_handoff(self, summary: Optional[str],
                         metadata: Optional[dict[str, Any]],
                         is_gate: bool = False) -> bool:
        """P2-S3: handoff must be kanban_complete(summary, metadata)."""
        if summary is None or (isinstance(summary, str) and not summary.strip()):
            raise ProtocolViolationError("handoff missing summary")
        md = metadata or {}
        if is_gate:
            v = md.get(VERDICT_KEY)
            if v not in (APPROVE, REJECT):
                raise ProtocolViolationError(
                    f"gate handoff missing/invalid verdict: {v!r}")
        return True

    def enforce_round_limit(self, debate_id: str, round_idx: int) -> bool:
        """P2-S1: return True if ``round_idx`` exceeds ``max_rounds`` (force-pass)."""
        prev = self._rounds.get(debate_id, 0)
        self._rounds[debate_id] = max(prev, round_idx)
        return self._rounds[debate_id] > self.max_rounds

    def enforce_cost(self, task_id: str) -> bool:
        """P2-S4: raise CostLimitExceeded if per-task spend crossed the threshold."""
        if self.cost_limit_per_task is None or self.cost is None:
            return False
        spent = self.cost.spent(task_id)
        if spent > self.cost_limit_per_task:
            raise CostLimitExceeded(
                f"task {task_id} spent {spent} > limit {self.cost_limit_per_task}")
        return False

    def detect_deadlock(self, completions_this_tick: int) -> bool:
        """P2-S2: ``idle_rounds`` consecutive ticks with no new completion -> deadlock."""
        if completions_this_tick > 0:
            self._idle_streak = 0
            return False
        self._idle_streak += 1
        return self._idle_streak >= self.idle_rounds

    # --- integrated tick ---------------------------------------------------

    def step(self, spawn_fn: Optional[SpawnFn] = None, *,
             gate_task_ids: Optional[set[str]] = None, **kw) -> SupervisorReport:
        """One dispatch tick + apply all gates to newly-completed tasks."""
        gate = gate_task_ids or set()
        report = SupervisorReport()
        before = set(self._done_ids)
        buckets = self.kanban.dispatch_once(spawn_fn, **kw)
        report.spawned = buckets.spawned
        done_now = {t.id for t in self.kanban.all_tasks() if t.status == DONE}
        new = done_now - before
        self._done_ids |= done_now
        report.new_completions = sorted(new)
        for tid in new:
            t = self.kanban.get_task(tid)
            if t is None:
                continue
            is_gate = tid in gate
            try:
                self.validate_handoff(t.summary, t.metadata, is_gate=is_gate)
            except ProtocolViolationError:
                report.violations.append(tid)
            try:
                self.enforce_cost(tid)
            except CostLimitExceeded:
                report.cost_breaches.append(tid)
                self._escalate(tid, "cost limit exceeded", report)
        if self.detect_deadlock(len(new)):
            report.idle = True
        return report

    # --- adversarial debate loop (P2-D2 + round-limit + idle) -------------

    def run_debate(self, orch, spawn_fn: SpawnFn, upstream_id: str,
                   gate_role: str, *, title: str = "gate",
                   max_rounds: Optional[int] = None,
                   gate_task_ids: Optional[set[str]] = None) -> DebateResult:
        """Drive U->gate until approve, round-limit force-pass, or idle escalate.

        Each round creates a fresh gate task (parent=upstream). A REJECT/ PENDING
        verdict loops (rework); ``> max_rounds`` rejects are force-passed (P2-S1);
        ``idle_rounds`` ticks with no gate completion escalate (P2-S2).
        """
        cap = self.max_rounds if max_rounds is None else max_rounds
        gate_ids = gate_task_ids if gate_task_ids is not None else set()
        rounds = 0
        last_gate: Optional[str] = None
        while rounds < cap:
            gid = orch.create_task(gate_role, title=title, body="adversarial review",
                                   parents=(upstream_id,))
            last_gate = gid
            gate_ids.add(gid)
            rep = self.step(spawn_fn, gate_task_ids=gate_ids)
            g = self.kanban.get_task(gid)
            if g is not None and g.status == DONE and gid in rep.new_completions:
                rounds += 1
                if g.verdict == APPROVE:
                    return DebateResult(DEBATE_PASS, rounds, gid)
                # REJECT or PENDING -> rework (loop)
                continue
            # gate did not complete this tick -> idle path
            if rep.idle or self.detect_deadlock(0):
                self._escalate(upstream_id, "deadlock: gate produced no verdict")
                return DebateResult(DEBATE_ESCALATED, rounds, gid,
                                    reason="deadlock")
        # exceeded cap -> force-pass the latest gate (P2-S1)
        if last_gate is not None:
            self._mark_forced(last_gate, cap)
        else:
            self._mark_forced(upstream_id, cap)
        return DebateResult(DEBATE_FORCED, cap, last_gate,
                            reason=f"round limit {cap} exceeded")

    # --- helpers -----------------------------------------------------------

    def _mark_forced(self, task_id: str, rounds: int) -> None:
        t = self.kanban.get_task(task_id)
        if t is None:
            return
        t.metadata[VERDICT_KEY] = APPROVE
        t.metadata["verdict_forced"] = True
        t.metadata["verdict_round"] = rounds

    def _escalate(self, task_id: str, reason: str,
                  report: Optional[SupervisorReport] = None) -> None:
        t = self.kanban.get_task(task_id)
        if t is None:
            return
        escalate = getattr(self.kanban, "escalate", None)
        if callable(escalate):
            escalate(task_id, reason)
        else:
            t.status = AWAITING_HUMAN
            t.metadata["escalation"] = reason
        if report is not None:
            report.escalations.append(task_id)
