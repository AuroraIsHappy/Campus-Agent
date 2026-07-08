"""Demo B pipeline: scan -> knowledge graph -> resources -> review plan + quiz.

``run_demo_b`` drives the full Demo B chain (B-F1..B-F6) end-to-end. Every
external seam (file extraction, KG node extraction, resource search, quiz
generation, memory) is injectable, so the deterministic e2e test runs with no
Hermes / no network / no real model. Mirrors the run-dir convention of
``campus.demo_a.pipeline`` and ``campus.demo_c.orchestrator``: artifacts +
``Verification.md`` land under ``~/.campus/runs/demo_b-<ts>/``.
"""
from __future__ import annotations
import dataclasses
import datetime as _dt
import json
import os

from campus.demo_b import (
    extractors as _ex, knowledge_graph as _kg, resource_search as _rs,
    review_planner as _rp, quiz as _quiz, checkers as _ck,
)
from campus.demo_b.types import RunResult, to_dict

try:  # KNOWLEDGE layer constant (campus.memory.types); fall back to literal.
    from campus.memory.types import KNOWLEDGE as _KNOWLEDGE_LAYER
except Exception:  # pragma: no cover - kept defensive for minimal envs
    _KNOWLEDGE_LAYER = "knowledge"

AWAITING = "delivered"


def new_run_dir(base: str = None) -> str:
    base = base or os.path.expanduser("~/.campus/runs")
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    d = os.path.join(base, f"demo_b-{ts}")
    os.makedirs(d, exist_ok=True)
    return d


def _write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _derive_topic(kg, path: str) -> str:
    titles = [n.title for n in kg.nodes if n.kind == "chapter"] or [n.title for n in kg.nodes]
    if titles:
        return titles[0]
    return os.path.basename(os.path.normpath(path or ".")) or "review"


def _jsonable(r: RunResult) -> dict:
    return {
        "ok": r.ok, "run_dir": r.run_dir, "final_status": r.final_status,
        "extraction_rate": r.extraction_rate, "kg_nodes": r.kg_nodes,
        "resource_count": r.resource_count, "plan_days": r.plan_days,
        "checks": [dataclasses.asdict(c) for c in r.checks],
        "artifacts": r.artifacts, "error": r.error,
    }


def _write_verification(run_dir, checks, rate, kg, candidates, plan, ids) -> str:
    lines = ["# Demo B Verification", "",
             f"- topic: {ids['topic']}", f"- extraction_rate: {rate:.2f}",
             f"- kg_nodes: {len(kg.nodes)}", f"- resources: {len(candidates)}",
             f"- plan_days: {len(plan.days)} (free {plan.free_minutes}m)", ""]
    lines += ["## Quality checks (B-F*/B-Q*)"]
    for c in checks:
        lines.append(f"- {'PASS' if c.passed else 'FAIL'} {c.name}: {c.detail}")
    p = os.path.join(run_dir, "Verification.md")
    _write(p, "\n".join(lines))
    return p


def run_demo_b(path: str, exam_date: str, *,
               free_minutes: int = 120, start_date: str | None = None,
               topic: str | None = None, slot_minutes: int = 20,
               extract_fn=None, searcher=None, quiz_fn=None,
               memory=None, run_dir: str | None = None,
               extractors=None) -> RunResult:
    """Drive Demo B end-to-end. Returns RunResult.

    For deterministic testing pass ``extractors`` (fake table) / ``searcher`` /
    ``quiz_fn`` / ``extract_fn`` stubs and a temp ``path``; everything runs with
    no Hermes / no network / no real model.
    """
    if run_dir is None:
        run_dir = new_run_dir()
    else:
        os.makedirs(run_dir, exist_ok=True)
    if start_date is None:
        start_date = _dt.date.today().isoformat()

    # 1. scan + extract (B-F1)
    results = _ex.extract_dir(path, extractors=extractors)
    rate, _ = _ex.extraction_rate(results)

    # 2. knowledge graph (B-F2)
    kg = _kg.build_kg(results, extract_fn=extract_fn)
    topic = topic or _derive_topic(kg, path)

    # 3. resources (B-F3 / B-Q1)
    candidates = _rs.search_resources(topic, searcher=searcher)

    # 4. review plan (B-F4 / B-Q3) + day-1 quiz (B-F5)
    plan = _rp.build_review_plan(kg, exam_date=exam_date, free_minutes=free_minutes,
                                 start_date=start_date, slot_minutes=slot_minutes,
                                 quiz_fn=quiz_fn)
    day1 = plan.days[0] if plan.days else None
    day1_quiz = (day1.quiz if day1 and day1.quiz
                 else _quiz.generate_quiz(topic, day1.content if day1 else "",
                                          quiz_fn=quiz_fn, day=1))

    # 5. quality gates (B-F*/B-Q*)
    checks = _ck.all_checks(results=results, kg=kg, candidates=candidates,
                            plan=plan, day1_quiz=day1_quiz)

    # 6. memory: sediment KG into the KNOWLEDGE layer (cross-session, S-MEMORY)
    if memory is not None:
        try:
            for n in kg.nodes:
                memory.remember(_KNOWLEDGE_LAYER, f"demo_b/{n.id}",
                                f"{n.kind}: {n.title} — {n.summary}",
                                metadata={"source_doc": n.source_doc})
        except Exception:
            pass

    # 7. write run-dir artifacts + Verification.md
    _write(os.path.join(run_dir, "kg.json"),
           json.dumps(to_dict({"nodes": kg.nodes, "edges": kg.valid_edges(),
                               "source_docs": kg.source_docs}),
                      ensure_ascii=False, indent=2))
    _write(os.path.join(run_dir, "plan.md"), _plan_md(plan, topic))
    _write(os.path.join(run_dir, "quiz_day1.json"),
           json.dumps(to_dict(day1_quiz), ensure_ascii=False, indent=2))
    _write(os.path.join(run_dir, "research_candidates.json"),
           json.dumps([r.__dict__ for r in candidates], ensure_ascii=False, indent=2))
    ver = _write_verification(run_dir, checks, rate, kg, candidates, plan,
                              {"topic": topic})

    ok = all(c.passed for c in checks) and len(candidates) >= 1
    result = RunResult(
        ok=ok, run_dir=run_dir, final_status=AWAITING if ok else "failed",
        extraction_rate=rate, kg_nodes=len(kg.nodes),
        resource_count=len(candidates), plan_days=len(plan.days),
        checks=checks, artifacts=sorted(os.path.join(run_dir, n)
                                        for n in os.listdir(run_dir)),
    )
    _write(os.path.join(run_dir, "run_result.json"),
           json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    _ = ver
    return result


def _plan_md(plan, topic: str) -> str:
    lines = [f"# Review Plan: {topic}", "",
             f"**Exam**: {plan.exam_date} | **free**: {plan.free_minutes}m | "
             f"**total**: {plan.total_minutes}m | within budget: {plan.within_budget}",
             "", "| Day | Date | Topics | Min | Quiz |", "|---|---|---|---|---|"]
    for d in plan.days:
        qn = len(d.quiz.questions) if d.quiz else 0
        lines.append(f"| {d.n} | {d.date} | {', '.join(d.topics)} | "
                     f"{d.est_minutes} | {qn}q |")
    return "\n".join(lines)
