"""L3 DAG topology + adversarial-pair helpers (architecture §4.2, P2-D1/D2).

Pure graph logic + thin Kanban-backed convenience helpers. No Hermes import.
"""
from __future__ import annotations
from collections import deque
from typing import Iterable

from campus.runtime.ports import (
    APPROVE, CyclicDAGError, MissingParentError, PENDING, REJECT,
)

__all__ = [
    "validate_dag", "topo_order", "create_adversarial_pair",
    "gate_verdict", "verdict_decision", "VERDICT_PASS", "VERDICT_REWORK", "VERDICT_PENDING",
]

VERDICT_PASS = "pass"
VERDICT_REWORK = "rework"
VERDICT_PENDING = "pending"


def validate_dag(parents_map: dict[str, Iterable[str]]) -> None:
    """Raise MissingParentError on unknown parent, CyclicDAGError on cycle (P2-D1)."""
    nodes = set(parents_map)
    # missing parents
    for n, ps in parents_map.items():
        for p in ps:
            if p not in nodes:
                raise MissingParentError(
                    f"task {n!r} references unknown parent {p!r}")
    # cycle detection (iterative DFS, graph: node -> its parents)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in nodes}
    for root in nodes:
        if color[root] != WHITE:
            continue
        stack = [(root, iter(parents_map[root]))]
        color[root] = GRAY
        while stack:
            node, it = stack[-1]
            advanced = False
            for parent in it:
                if color[parent] == GRAY:
                    raise CyclicDAGError(
                        f"cycle detected: {node!r} -> {parent!r}")
                if color[parent] == WHITE:
                    color[parent] = GRAY
                    stack.append((parent, iter(parents_map[parent])))
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                stack.pop()


def topo_order(parents_map: dict[str, Iterable[str]]) -> list[str]:
    """Kahn's algorithm: parents before children (validates first)."""
    validate_dag(parents_map)
    children: dict[str, list[str]] = {n: [] for n in parents_map}
    indeg: dict[str, int] = {n: 0 for n in parents_map}
    for n, ps in parents_map.items():
        uniq = set(ps)
        indeg[n] = len(uniq)
        for p in uniq:
            children[p].append(n)
    q = deque(sorted(n for n, d in indeg.items() if d == 0))
    out: list[str] = []
    while q:
        u = q.popleft()
        out.append(u)
        for c in children[u]:
            indeg[c] -= 1
            if indeg[c] == 0:
                q.append(c)
    return out


def create_adversarial_pair(orch, *, upstream_role: str, gate_role: str,
                            upstream_title: str, gate_title: str,
                            goal: str) -> tuple[str, str]:
    """Create Planner->Critic / Writer->Reviewer style pair linked by parents.

    The gate task is BLOCKED until the upstream task completes (P2-D2).
    Returns (upstream_task_id, gate_task_id).
    """
    uid = orch.create_task(upstream_role, title=upstream_title, body=goal)
    gid = orch.create_task(gate_role, title=gate_title, body=goal, parents=(uid,))
    return uid, gid


def gate_verdict(kanban, gate_task_id: str) -> str:
    """Read the gate task's metadata['verdict'] (PENDING if absent)."""
    t = kanban.get_task(gate_task_id)
    return t.verdict if t else PENDING


def verdict_decision(kanban, gate_task_id: str) -> str:
    """Map a gate task's verdict to a routing decision (P2-D2)."""
    v = gate_verdict(kanban, gate_task_id)
    if v == APPROVE:
        return VERDICT_PASS
    if v == REJECT:
        return VERDICT_REWORK
    return VERDICT_PENDING
