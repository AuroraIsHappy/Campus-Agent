"""MetaAgent → Odyssey execution bridge (Phase 8 Step 1).

The Phase 2/3 engine (Orchestrator + Supervisor + role DAG + adversarial debates)
is real and tested, but Phase 7's ``/agent/run`` bypassed it with a keyword
classifier → deterministic ``phase7`` shortcut. This module is the missing bridge:
it turns a free-text message into an *executed* multi-agent run.

Flow::

    message
      -> MetaAgent.classify  (short | long)
      -> MetaAgent.build_dag (role DAG with parents)
      -> Orchestrator.create_task (per role, parents-encoded)
      -> Supervisor.run_debate (Planner<->Critic, Writer<->Reviewer)
      -> artifacts written to RunStore/ArtifactStore

The long-task DAG mirrors demo_a's proven 8-role shape but is driven by a
*generic* role-turn factory (``build_generic_turn``) that uses the role's profile
``system_prompt`` + the task body — no demo_a-specific ``ctx`` threading. This
makes it work for any long-horizon request, not just 社会实践策划案.

For short tasks, a single ``hermes_direct`` node runs one LLM turn and returns.

Deterministic offline path: when no real LLM is available, ``make_offline_turn``
returns canned APPROVE verdicts + a templated summary so the DAG topology +
Supervisor gates still execute (and stay testable with no Hermes / no network).
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from campus.meta_agent.meta_agent import MetaAgent, LONG_DAG
from campus.meta_agent.skill_discovery import SkillRegistry
from campus.odyssey.orchestrator import CostTracker, Orchestrator, TurnOutcome
from campus.odyssey.supervisor import Supervisor
from campus.profiles.loader import ProfileLoader
from campus.runtime.in_memory import InMemoryKanban
from campus.runtime.ports import APPROVE, REJECT, Task
from campus.runtime.stores import ArtifactStore, RunStore

__all__ = ["MetaRunner", "MetaRunResult", "build_generic_turn", "make_offline_turn"]


@dataclass
class MetaRunResult:
    ok: bool
    run_id: str = ""
    kind: str = ""               # short | long
    domain: str = ""
    dag: list[dict] = field(default_factory=list)
    debates: list[dict] = field(default_factory=list)
    final_status: str = ""
    summary: str = ""
    artifacts: list[dict] = field(default_factory=list)
    error: str = ""


def build_generic_turn(loader: ProfileLoader,
                       memory_snippet: str = "") -> Callable[[dict, Task], TurnOutcome]:
    """Build a real-LLM turn_fn for the generic DAG.

    Each role turn = profile.system_prompt + task.title/body (+ optional memory
    snippet) → ``llm_turn`` → parsed TurnOutcome. Gate roles emit APPROVE/REJECT;
    content roles return the raw deliverable + any embedded JSON.
    """
    from campus.runtime.llm_turn import llm_turn

    def turn(profile: dict, task: Task) -> TurnOutcome:
        # inject recalled memory context into the task body so roles see user prefs
        body = task.body or ""
        if memory_snippet:
            body = f"=== USER CONTEXT (memory) ===\n{memory_snippet}\n\n=== TASK ===\n{body}"
            task.body = body  # mutate so downstream roles inherit via kanban summary
        return llm_turn(profile, task)

    return turn


def make_offline_turn(loader: ProfileLoader,
                      message: str = "") -> Callable[[dict, Task], TurnOutcome]:
    """Deterministic offline turn_fn: APPROVE gates, templated content for others.

    Keeps the DAG topology + Supervisor gates fully exercisable without Hermes /
    LLM / network. Mirrors demo_a's ``make_offline_turn`` philosophy.
    """
    gate_roles = {"critic", "reviewer"}

    def turn(profile: dict, task: Task) -> TurnOutcome:
        role = (profile.get("role") or task.assignee or "").strip()
        if role in gate_roles:
            return TurnOutcome(
                summary=f"[offline] {role} approves — gate passed.",
                metadata={"verdict": APPROVE}, tokens=8)
        # content role: produce a templated deliverable from the task body
        title = task.title or role
        body = (task.body or "")[:400]
        summary = (
            f"## {title}\n\n"
            f"（离线模板产出）针对用户请求「{message[:80]}」，{role} 角色完成了一轮处理。\n\n"
            f"输入摘要：{body}\n\n"
            f"下一步：交由后续角色继续。"
        )
        return TurnOutcome(summary=summary, metadata={}, tokens=max(1, len(summary) // 4))

    return turn


class MetaRunner:
    """Bridge MetaAgent classification → Odyssey DAG execution.

    Usage (real)::

        runner = MetaRunner()
        result = runner.run("帮我做一份低碳校园实践策划案", mode="real")

    Usage (offline, deterministic)::

        result = runner.run("我想学 Linux", mode="offline")
    """

    def __init__(self, *, meta: Optional[MetaAgent] = None,
                 loader: Optional[ProfileLoader] = None) -> None:
        self.meta = meta or MetaAgent(skill_registry=SkillRegistry())
        self.loader = loader or ProfileLoader()

    def run(self, message: str, *, mode: str = "offline",
            domain: str = "", context: Optional[dict] = None,
            memory_snippet: str = "") -> MetaRunResult:
        """Classify → build DAG → execute via Orchestrator+Supervisor → persist."""
        from campus.runtime.llm_config import resolve_mode, require_real_llm

        decision = self.meta.classify(message)
        dag = self.meta.build_dag(decision)
        skills = decision.skills or []

        # persist a run record up front
        runs = RunStore()
        artifacts = ArtifactStore(runs)
        rec = runs.create(
            message=message, intent=f"meta_{decision.kind}",
            domain=domain or ("club" if decision.kind == "long" else "general"),
            selected_workflow=f"meta_agent_{decision.kind}",
            context=context or {}, status="running")
        artifacts.write_text(rec.id, "Plan.md",
                             f"# Meta-Agent Plan\n\n- message: {message}\n"
                             f"- kind: {decision.kind}\n- reason: {decision.reason}\n"
                             f"- skills: {skills}\n- DAG roles: "
                             f"{[n['role'] for n in dag]}\n")

        # choose turn_fn by mode
        resolved = resolve_mode(mode)
        real = False
        if resolved != "offline":
            real, status = require_real_llm(mode)
            if resolved == "real" and not status.get("ok"):
                runs.update(rec.id, status="failed",
                            error=status.get("error", "LLM not ready"))
                return MetaRunResult(ok=False, run_id=rec.id, kind=decision.kind,
                                     error=status.get("error", ""))

        if real:
            turn_fn = build_generic_turn(self.loader, memory_snippet)
        else:
            turn_fn = make_offline_turn(self.loader, message)

        # execute
        try:
            if decision.kind == "short":
                final_status, summary, debates = self._run_short(
                    message, dag, turn_fn, skills)
            else:
                final_status, summary, debates = self._run_long(
                    message, dag, turn_fn)
        except Exception as e:
            runs.update(rec.id, status="failed", error=str(e))
            artifacts.write_text(rec.id, "Status.md",
                                 f"# Status\n\n- status: failed\n- error: {e}\n")
            return MetaRunResult(ok=False, run_id=rec.id, kind=decision.kind,
                                 error=str(e), dag=dag)

        # persist artifacts
        artifacts.write_text(rec.id, "Status.md",
                             f"# Status\n\n- status: {final_status}\n- kind: {decision.kind}\n")
        verification = self._verification(decision, debates, final_status)
        artifacts.write_text(rec.id, "Verification.md", verification)
        result_data = {"ok": True, "kind": decision.kind, "domain": domain,
                       "summary": summary, "debates": debates, "dag": dag,
                       "skills": skills, "mode": "real" if real else "offline"}
        artifacts.write_json(rec.id, "run_result.json", result_data)
        manifest = artifacts.list(rec.id)
        runs.update(rec.id, status=final_status, result=result_data, artifacts=manifest)

        return MetaRunResult(
            ok=True, run_id=rec.id, kind=decision.kind, domain=domain,
            dag=dag, debates=debates, final_status=final_status,
            summary=summary, artifacts=manifest)

    def _run_short(self, message: str, dag: list[dict],
                   turn_fn, skills: list[str]) -> tuple[str, str, list[dict]]:
        """Single-node DAG: one hermes_direct turn, no adversarial debate."""
        kanban = InMemoryKanban("meta-short")
        orch = Orchestrator(kanban)
        cost = CostTracker()
        spawn = orch.make_profile_spawn_fn(self.loader, turn_fn, cost)
        node = dag[0]
        tid = orch.create_task(
            "meta_agent", title="direct", body=message,
            parents=(), skills=tuple(skills))
        orch.run_to_completion(spawn, max_ticks=4)
        t = kanban.get_task(tid)
        summary = (t.summary if t else "") or "(no output)"
        return "done", summary, []

    def _run_long(self, message: str, dag: list[dict],
                  turn_fn) -> tuple[str, str, list[dict]]:
        """Full 8-role DAG with two adversarial debates (Planner↔Critic, Writer↔Reviewer).

        Mirrors demo_a's proven topology but with generic role turns (no
        demo_a-specific ctx threading). The DAG nodes chain via ``parents``;
        Supervisor drives the two gate debates.
        """
        kanban = InMemoryKanban("meta-long")
        orch = Orchestrator(kanban)
        cost = CostTracker()
        spawn = orch.make_profile_spawn_fn(self.loader, turn_fn, cost)
        sup = Supervisor(kanban, max_rounds=3, cost=cost)
        debates: list[dict] = []

        # 1. planner
        pid = self._run_one(orch, spawn, "planner", "plan", message)
        # 2. critic debate (Planner↔Critic)
        d1 = sup.run_debate(orch, spawn, pid, "critic", title="plan-gate")
        debates.append({"pair": "Planner<->Critic", "outcome": d1.outcome, "rounds": d1.rounds})

        # 3-5. researcher → source_verifier → source_ranker (chain)
        rid = self._run_one(orch, spawn, "researcher", "research",
                            f"为以下任务检索可靠信息源：\n{message}", parents=(pid,))
        vid = self._run_one(orch, spawn, "source_verifier", "verify",
                            "验证上一步信息源的真实性与可达性。", parents=(rid,))
        sid = self._run_one(orch, spawn, "source_ranker", "rank",
                            "按相关性/权威性/时效打分排序信息源。", parents=(vid,))
        # 6. writer
        wid = self._run_one(orch, spawn, "writer", "write",
                            f"基于已验证信息源,为用户完成交付物：\n{message}", parents=(sid,))
        # 7. reviewer debate (Writer↔Reviewer)
        d2 = sup.run_debate(orch, spawn, wid, "reviewer", title="delivery-gate")
        debates.append({"pair": "Writer<->Reviewer", "outcome": d2.outcome, "rounds": d2.rounds})
        # 8. final summary from writer
        wt = kanban.get_task(wid)
        summary = (wt.summary if wt else "") or "(no writer output)"
        final_status = "done" if d2.outcome != "escalated" else "awaiting_human"
        return final_status, summary, debates

    def _run_one(self, orch: Orchestrator, spawn, role: str,
                 title: str, body: str, parents=()) -> str:
        tid = orch.create_task(role, title=title, body=body, parents=parents)
        orch.run_to_completion(spawn, max_ticks=8)
        return tid

    def _verification(self, decision, debates: list[dict], final_status: str) -> str:
        lines = [f"# Meta-Agent Verification", "",
                 f"- kind: {decision.kind}", f"- reason: {decision.reason}",
                 f"- final_status: {final_status}", ""]
        for d in debates:
            lines += [f"## {d['pair']}", f"- outcome: {d['outcome']}",
                      f"- rounds: {d['rounds']}", ""]
        lines += ["## DAG roles"]
        for n in (decision.skills and [] or []):
            lines.append(f"- {n}")
        return "\n".join(lines)
