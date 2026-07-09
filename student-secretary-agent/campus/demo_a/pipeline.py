"""Demo A pipeline (T9): builds the 5-checkpoint Odyssey DAG, drives it with the
Orchestrator + Supervisor (two adversarial debates: Planner<->Critic,
Writer<->Reviewer), then escalates to awaiting_human (A-F4, no send).

Mirrors campus/demo_c/orchestrator.py run-dir convention. Deterministic test
path: inject a fake turn_fn (or mock campus.runtime.llm_turn.ask_llm) so the whole
DAG runs with no Hermes / no LLM / no network.
"""
from __future__ import annotations
import dataclasses
import datetime as _dt
import json
import os
import re

from campus.odyssey.orchestrator import CostTracker, Orchestrator
from campus.odyssey.supervisor import Supervisor
from campus.profiles.loader import ProfileLoader
from campus.runtime.in_memory import InMemoryKanban
from campus.runtime.paths import runs_dir

from campus.demo_a import checkers
from campus.demo_a.role_turns import (
    email_body, make_demo_a_turn, planner_body, ranker_body,
    researcher_body, verifier_body, writer_body,
)
from campus.demo_a.types import Brief, RunResult, SampleSpec

AWAITING = "awaiting_human"


def new_run_dir(base: str = None) -> str:
    base = base or runs_dir()
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    d = os.path.join(base, f"demo_a-{ts}")
    os.makedirs(d, exist_ok=True)
    return d


def _run_one(orch, spawn, role, title, body, parents=()) -> str:
    tid = orch.create_task(role, title=title, body=body, parents=parents)
    orch.run_to_completion(spawn, max_ticks=8)
    return tid


def _escalate(kanban, task_id: str, reason: str) -> None:
    fn = getattr(kanban, "escalate", None)
    if callable(fn):
        fn(task_id, reason)
    else:
        t = kanban.get_task(task_id)
        if t is not None:
            t.status = AWAITING


def _count_email_segments(emails_text: str, targets) -> int:
    """How many outreach targets have a segment in the email draft (A-F3).

    Target-name-anchored so multi-paragraph emails don't over-count (a bare
    blank-line split miscounts 1-per-paragraph). Falls back to blank-line blocks
    only if no target names are available.
    """
    if not emails_text:
        return 0
    names = []
    for t in targets or []:
        n = t.get("name") if isinstance(t, dict) else getattr(t, "name", "")
        if n:
            names.append(str(n))
    if not names:
        return len([p for p in emails_text.replace("\r", "").split("\n\n")
                    if p.strip()])
    return sum(1 for n in names if n in emails_text)


def _write_verification(run_dir, debates, checks, verify, ctx, ids) -> str:
    lines = ["# Demo A Verification", ""]
    for d in debates:
        lines += [f"## {d['pair']}", f"- outcome: {d['outcome']}",
                  f"- rounds: {d['rounds']}", ""]
    lines += ["## Quality checks (A-Q1/Q3/Q4)"]
    for c in checks:
        lines.append(f"- {'PASS' if c.passed else 'FAIL'} {c.name}: {c.detail}")
    lines += ["", "## Source verification (A-Q2)",
              f"- {len(verify)} target(s) checked"]
    lines += [f"- {v['name']} -> {v['url']} status={v['status']} "
              f"reachable={v['reachable']}" for v in verify]
    lines += ["", "## Outreach targets (A-F2)"]
    lines += [f"- {t.get('name')}: {t.get('visit_reason')} "
              f"(source: {t.get('contact_source')}, url: {t.get('url')})"
              for t in ctx.get("targets", [])]
    lines += ["", f"task ids: {ids}", ""]
    p = os.path.join(run_dir, "Verification.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return p


def _list_artifacts(run_dir) -> list[str]:
    return sorted(os.path.join(run_dir, n) for n in os.listdir(run_dir))


def _jsonable(r: RunResult) -> dict:
    return {
        "ok": r.ok, "run_dir": r.run_dir, "final_status": r.final_status,
        "outreach_count": r.outreach_count, "email_segments": r.email_segments,
        "checks": [dataclasses.asdict(c) for c in r.checks],
        "debates": r.debates, "artifacts": r.artifacts, "error": r.error,
    }


def run_demo_a(sample, brief, *, kanban=None, loader=None, turn=None,
               turn_factory=None,
               run_dir=None, sup_max_rounds: int = 3,
               url_opener=None, board: str = "campus-demo-a") -> RunResult:
    """Drive the Demo A DAG end-to-end. Returns RunResult.

    For deterministic testing: pass ``turn`` (a fake turn_fn) or monkeypatch
    ``campus.runtime.llm_turn.ask_llm``; pass ``url_opener`` to avoid the network.
    """
    sample = sample if isinstance(sample, SampleSpec) else SampleSpec(raw=str(sample))
    if isinstance(brief, Brief):
        pass
    elif isinstance(brief, dict):
        brief = Brief(**{k: brief.get(k, "") for k in ("topic", "region", "window")})
    else:
        brief = Brief()
    if kanban is None:
        kanban = InMemoryKanban(board)
    if loader is None:
        loader = ProfileLoader()
    if run_dir is None:
        run_dir = new_run_dir()

    ctx: dict = {"sample": sample, "brief": brief}
    if turn_factory is not None:
        turn = turn_factory(run_dir, ctx)
    elif turn is None:
        turn = make_demo_a_turn(loader, run_dir, ctx)

    cost = CostTracker()
    orch = Orchestrator(kanban)
    spawn = orch.make_profile_spawn_fn(loader, turn, cost)
    sup = Supervisor(kanban, max_rounds=sup_max_rounds)
    debates: list[dict] = []

    # 1. Planner
    pid = _run_one(orch, spawn, "planner", "plan", planner_body(sample, brief))
    # 2. Critic debate on the plan (A-Q5 left side)
    d_plan = sup.run_debate(orch, spawn, pid, "critic", title="plan-gate")
    debates.append({"pair": "Planner<->Critic", "outcome": d_plan.outcome,
                    "rounds": d_plan.rounds, "plan_task": pid})
    # 3. Researcher -> 4. SourceVerifier -> 5. SourceRanker
    rid = _run_one(orch, spawn, "researcher", "research outreach",
                   researcher_body(ctx), parents=(pid,))
    vid = _run_one(orch, spawn, "source_verifier", "verify sources",
                   verifier_body(ctx), parents=(rid,))
    sid = _run_one(orch, spawn, "source_ranker", "rank targets",
                   ranker_body(ctx), parents=(vid,))
    # 6. Writer
    wid = _run_one(orch, spawn, "writer", "write proposal",
                   writer_body(ctx), parents=(sid,))
    # 7. Reviewer debate on the proposal (A-Q5 right side)
    d_prop = sup.run_debate(orch, spawn, wid, "reviewer", title="proposal-gate")
    debates.append({"pair": "Writer<->Reviewer", "outcome": d_prop.outcome,
                    "rounds": d_prop.rounds, "writer_task": wid})
    # 8. Email (B1: draft only)
    eid = _run_one(orch, spawn, "email", "draft emails",
                   email_body(ctx), parents=(wid,))
    # 9. Escalate -> awaiting_human (A-F4, NO send anywhere)
    _escalate(kanban, eid, "awaiting human confirm before any send (B1)")

    # 10. Quality checks (A-Q1/Q3/Q4) + URL reachability (A-Q2) + Verification.md
    proposal = ctx.get("proposal", "")
    checks = [
        checkers.check_format_adherence(proposal, sample),
        checkers.check_completeness(proposal),
        checkers.check_geographic_plausibility(proposal),
    ]
    targets = ctx.get("targets", [])
    verify = checkers.verify_urls(targets, opener=url_opener) if targets else []
    ids = {"planner": pid, "researcher": rid, "verifier": vid,
           "ranker": sid, "writer": wid, "email": eid}
    _write_verification(run_dir, debates, checks, verify, ctx, ids)

    final = kanban.get_task(eid)
    final_status = final.status if final else AWAITING
    segs = _count_email_segments(ctx.get("emails", ""), targets)
    ok = (final_status == AWAITING and len(targets) >= 3
          and segs == len(targets) and all(c.passed for c in checks))
    result = RunResult(ok=ok, run_dir=run_dir, final_status=final_status,
                       outreach_count=len(targets), email_segments=segs,
                       checks=checks, debates=debates,
                       artifacts=_list_artifacts(run_dir))
    with open(os.path.join(run_dir, "run_result.json"), "w", encoding="utf-8") as f:
        json.dump(_jsonable(result), f, ensure_ascii=False, indent=2)
    return result
