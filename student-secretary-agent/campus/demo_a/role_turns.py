"""Demo A role-turn dispatcher (T5): builds role-specific task bodies, runs the
shared ``llm_turn``, persists artifacts to run_dir, and threads context (``ctx``)
between roles.

ctx carries the evolving deliverables (plan, candidates, verified, targets,
proposal, emails) because the injected ``turn_fn(profile, task)`` receives no
kanban handle (Phase 2 seam). Gate roles (critic/reviewer) read ctx to know what
to review, since run_debate creates their tasks with a bare "adversarial review"
body. Pure helpers (``coerce_targets`` etc.) are unit-tested directly.
"""
from __future__ import annotations
import dataclasses
import json
import os

from campus.runtime.llm_turn import llm_turn
from campus.runtime.ports import Task
from campus.demo_a import renderers
from campus.demo_a.types import OutreachTarget


# --- role-specific task bodies (non-gate roles; gate bodies are built in turn) -

def planner_body(sample, brief) -> str:
    cols = ", ".join(sample.columns) if sample.columns else "(infer from sample)"
    return (
        "Write a checkpointed PLAN for a 社会实践策划案 (social-practice proposal).\n"
        f"Topic: {brief.topic}; Region: {brief.region}; Window: {brief.window}\n"
        f"Sample tone to mirror: {sample.tone}; sample columns: [{cols}]\n"
        "Checkpoints: Research -> Verify -> Rank -> Write -> Review -> Email.\n"
        "Output the plan as markdown.")


def researcher_body(ctx) -> str:
    b = ctx["brief"]
    return (
        f"Find >=3 outreach targets (参访地/外联对象) for topic '{b.topic}' "
        f"in region '{b.region}'. Each must be a real, findable entity with a URL.\n"
        "Return ONE ```json block: a list of objects with keys "
        "name, visit_reason, contact_source, url.\n"
        "Plan context:\n" + (ctx.get("plan", "") or "")[:1500])


def verifier_body(ctx) -> str:
    return (
        "For each candidate below, confirm the url is real and the entity exists "
        "(HTTP 200). Return ONE ```json block: list of "
        "{name, url, verified(bool), evidence}.\nCandidates:\n"
        + json.dumps(ctx.get("candidates", []), ensure_ascii=False)[:2000])


def ranker_body(ctx) -> str:
    return (
        "Score and rank these verified targets by fit/recency/authority; keep the "
        "top >=3. Return ONE ```json block: list of "
        "{name, visit_reason, contact_source, url, score}.\nVerified:\n"
        + json.dumps(ctx.get("verified", []), ensure_ascii=False)[:2000])


def writer_body(ctx) -> str:
    sample = ctx["sample"]
    cols = ", ".join(sample.columns) if sample.columns else "(infer from sample)"
    return (
        "Write the 社会实践策划案 as markdown. Mirror sample tone="
        f"{sample.tone}; columns=[{cols}]. MUST include sections: 预算(budget), "
        "时间表(timeline), 安全预案(safety). Use only the verified targets below; "
        "do NOT fabricate names, places, policies, or contacts.\nTargets:\n"
        + json.dumps(ctx.get("targets", []), ensure_ascii=False)[:2000])


def email_body(ctx) -> str:
    return (
        "Write ONE copy-paste outreach email segment per target, plain text, "
        f"matching tone={ctx['sample'].tone}. Separate segments with a blank line. "
        "Do NOT call any send/SMTP/gateway tool (B1: draft only).\nTargets:\n"
        + json.dumps(ctx.get("targets", []), ensure_ascii=False)[:2000])


# --- helpers (pure, unit-tested) ---------------------------------------------

def _set_body(task: Task, body: str) -> Task:
    if body == (task.body or ""):
        return task
    return dataclasses.replace(task, body=body)


def coerce_targets(payload) -> list[OutreachTarget]:
    """Normalize an LLM payload (list of dicts) into OutreachTarget list."""
    if not isinstance(payload, list):
        return []
    out = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        t = OutreachTarget(
            name=str(item.get("name", "")).strip(),
            visit_reason=str(item.get("visit_reason", "")).strip(),
            contact_source=str(item.get("contact_source", "")).strip(),
            url=str(item.get("url", "")).strip(),
            score=float(item.get("score", 0) or 0))
        if t.name:
            out.append(t)
    return out


def _write(run_dir: str, name: str, text: str) -> str:
    p = os.path.join(run_dir, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


def persist_role(role: str, out, ctx: dict, run_dir: str) -> list[str]:
    """Write role artifacts to run_dir + update ctx. Returns artifact paths."""
    arts: list[str] = []
    summary = out.summary or ""
    payload = (out.metadata or {}).get("payload")

    if role == "planner":
        ctx["plan"] = summary
        arts.append(_write(run_dir, "Plan.md", summary))
    elif role == "researcher":
        targets = coerce_targets(payload)
        ctx["candidates"] = [dataclasses.asdict(t) for t in targets]
        arts.append(_write(run_dir, "outreach_candidates.json",
                           json.dumps(ctx["candidates"], ensure_ascii=False, indent=2)))
    elif role == "source_verifier":
        ctx["verified"] = payload if isinstance(payload, list) else ctx.get("candidates", [])
        arts.append(_write(run_dir, "verification_evidence.json",
                           json.dumps(ctx["verified"], ensure_ascii=False, indent=2)))
    elif role == "source_ranker":
        targets = coerce_targets(payload) or coerce_targets(ctx.get("verified"))
        ctx["targets"] = [dataclasses.asdict(t) for t in targets]
        arts.append(_write(run_dir, "ranked_targets.json",
                           json.dumps(ctx["targets"], ensure_ascii=False, indent=2)))
    elif role == "writer":
        ctx["proposal"] = summary
        arts.append(_write(run_dir, "proposal.md", summary))
        arts.extend(render_proposal(summary, run_dir))
    elif role == "email":
        ctx["emails"] = summary
        arts.append(_write(run_dir, "emails.txt", summary))
    # critic/reviewer: verdict lives in metadata (recorded by run_debate)
    return arts


def md_outline(md: str):
    """Extract a (title, [bullets]) outline from markdown ## sections."""
    outline = []
    cur = None
    for line in md.splitlines():
        if line.startswith("## "):
            cur = (line[3:].strip(), [])
            outline.append(cur)
        elif cur is not None and (line.startswith("- ") or line.startswith("* ")):
            cur[1].append(line[2:].strip())
    if not outline:
        outline.append(("社会实践策划案", [md[:120]]))
    return outline


def budget_rows(md: str) -> list[dict]:
    """Pull bullet items under the first 预算/budget section; fallback defaults."""
    rows = []
    in_budget = False
    for line in md.splitlines():
        if any(k in line for k in ("预算", "budget", "经费")) and line.lstrip().startswith("#"):
            in_budget = True
            continue
        if in_budget and line.lstrip().startswith("#"):
            in_budget = False
        if in_budget and (line.startswith("- ") or line.startswith("* ")):
            rows.append({"item": line[2:].strip()})
    return rows or [{"item": "交通费"}, {"item": "餐饮费"}, {"item": "材料费"}]


def render_proposal(proposal_md: str, run_dir: str) -> list[str]:
    """Best-effort render to .docx/.pptx/.xlsx; skip silently if libs absent."""
    arts = []
    try:
        arts.append(renderers.to_docx(proposal_md, os.path.join(run_dir, "proposal.docx")))
    except Exception:
        pass
    try:
        arts.append(renderers.to_pptx(md_outline(proposal_md),
                                      os.path.join(run_dir, "proposal.pptx")))
    except Exception:
        pass
    try:
        arts.append(renderers.to_xlsx(budget_rows(proposal_md),
                                      os.path.join(run_dir, "budget.xlsx")))
    except Exception:
        pass
    return arts


# --- the turn_fn factory -----------------------------------------------------

def make_demo_a_turn(loader, run_dir: str, ctx: dict):
    """Return a turn_fn(profile, task)->TurnOutcome bound to run_dir + ctx."""
    def turn(profile, task):
        role = profile.get("role", "")
        body = task.body or ""
        if role == "critic":
            body = ("Adversarial review of this PLAN (do not rewrite it). Check "
                    "feasibility, checkpoint coverage (Research->Verify->Rank->"
                    "Write->Review->Email), sample-format fit, fabrication risk.\n"
                    "PLAN:\n" + (ctx.get("plan") or "(missing)"))
        elif role == "reviewer":
            body = ("Adversarial review of this PROPOSAL (do not rewrite it). Check "
                    "format adherence to sample, no fabricated facts, "
                    "budget+timeline+safety present, geographic plausibility.\n"
                    "PROPOSAL:\n" + (ctx.get("proposal") or "(missing)"))
        out = llm_turn(profile, _set_body(task, body))
        persist_role(role, out, ctx, run_dir)
        return out
    return turn
