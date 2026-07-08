"""Real-GLM injection points for Demo B (Phase 5 -> 真模型验收).

Wraps ``campus.runtime.llm_turn.ask_llm`` + ``extract_json`` into the three
seams ``run_demo_b`` already accepts: ``extract_fn`` (knowledge graph),
``quiz_fn``, ``searcher``. Each builds a strict-JSON prompt, parses defensively
(bad/missing fields are skipped, never crash the pipeline), and falls back to
the deterministic default if the model returns nothing usable.

Run for real (conda python; hermes_cli lives in the venv site-packages):

    export PYTHONPATH=student-secretary-agent/.venv/Lib/site-packages
    cd student-secretary-agent
    python -m campus.demo_b.llm <讲义目录> <考试日>            # prints run_dir
    # or:
    python -c "from campus.demo_b.llm import run_demo_b_live as r; \
x=r('<讲义目录>','2026-08-20'); print(x.ok, x.run_dir, x.kg_nodes)"

Vendor-neutral: model/provider are parameters (default glm-4.5-air / zai, the
combo proven in the smoke test). Swap to glm-4.6 / deepseek / qwen via args.
"""
from __future__ import annotations
import argparse
import json
from typing import Optional

from campus.demo_b.types import KGNode, KG_KINDS, QuizQ
from campus.demo_b.resource_search import default_searcher
from campus.runtime.llm_turn import ask_llm, extract_json

__all__ = [
    "DEFAULT_MODEL", "DEFAULT_PROVIDER",
    "make_extract_fn", "make_quiz_fn", "make_searcher",
    "run_demo_b_live",
]

DEFAULT_MODEL = "glm-4.5-air"      # proven in smoke test; fast & cheap
DEFAULT_PROVIDER = "zai"


def _call_json(prompt: str, *, model: str, provider: str, hint: str = "list"):
    """ask_llm -> extract_json. Returns parsed list/dict or None (never raises)."""
    try:
        raw, rc = ask_llm(prompt, model=model, provider=provider)
    except Exception:
        return None
    if rc != 0 or not raw:
        return None
    payload = extract_json(raw)
    if hint == "list" and isinstance(payload, dict):
        for v in payload.values():           # model wrapped array under a key
            if isinstance(v, list):
                payload = v
                break
    return payload


# ---------------- KG extraction (B-F2, real model) ----------------

_KG_PROMPT = """你是知识图谱抽取器，服务于期末复习。从下面讲义文本中抽取结构化知识节点。
对每个节点输出 JSON：{"kind": ..., "title": ..., "summary": ...}
- kind 必须是之一：chapter（章节标题）、concept（核心概念）、formula（重要公式）、question_type（常见题型）、key_point（重点/易考点）
- title：简短名称；summary：一句话说明（≤40字）
- 优先 chapter 与 concept，其次 formula/question_type/key_point；最多 15 个，按文本出现顺序。

讲义来源：{src}
讲义文本（节选）：
---
{text}
---
只输出一个 JSON 数组，例如 [{"kind":"chapter","title":"进程调度","summary":"..."}]，不要任何额外文字。"""


def _parse_kgnodes(payload, source_doc: str) -> list[KGNode]:
    out: list[KGNode] = []
    items = payload if isinstance(payload, list) else []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            continue
        kind = str(it.get("kind", "")).strip().lower()
        if kind not in KG_KINDS:
            continue
        title = str(it.get("title", "")).strip()
        if not title:
            continue
        summary = str(it.get("summary", "")).strip()
        out.append(KGNode(id=f"{kind}-{i}", kind=kind, title=title,
                          summary=summary, source_doc=source_doc))
    return out


def make_extract_fn(model: str = DEFAULT_MODEL, provider: str = DEFAULT_PROVIDER):
    """extract_fn(text, source_doc) -> list[KGNode] backed by GLM."""
    def _fn(text: str, source_doc: str) -> list[KGNode]:
        snippet = (text or "")[:4000]
        if not snippet.strip():
            return []
        payload = _call_json(_KG_PROMPT.replace("{src}", source_doc).replace("{text}", snippet),
                             model=model, provider=provider)
        return _parse_kgnodes(payload, source_doc)
    return _fn


# ---------------- Quiz generation (B-F5, real model) ----------------

_QUIZ_PROMPT = """你是期末复习出题官。基于下面主题与复习内容，出 {n} 道考察理解的题（不要纯死记）。
每题输出 JSON：{"q": ..., "answer": ..., "explanation": ..., "options": ...}
- q：题干；answer：正确答案；explanation：简短解析（≤50字）
- options：选择题给 4 个选项的字符串数组；简答/计算题给 null

主题：{topic}
复习内容：
---
{content}
---
只输出一个 JSON 数组，例如 [{"q":"...","answer":"...","explanation":"...","options":["A","B","C","D"]}]。"""


def _parse_quizq(payload) -> list[QuizQ]:
    out: list[QuizQ] = []
    for it in (payload if isinstance(payload, list) else []):
        if not isinstance(it, dict):
            continue
        q = str(it.get("q") or it.get("question") or "").strip()
        ans = str(it.get("answer") or it.get("a") or "").strip()
        if not q or not ans:
            continue
        opts = it.get("options")
        opts = [str(o) for o in opts] if isinstance(opts, list) and len(opts) >= 2 else None
        out.append(QuizQ(q=q, answer=ans,
                         explanation=str(it.get("explanation", "")).strip(),
                         options=opts))
    return out


def make_quiz_fn(model: str = DEFAULT_MODEL, provider: str = DEFAULT_PROVIDER):
    """quiz_fn(topic, content, n) -> list[QuizQ] backed by GLM."""
    def _fn(topic: str, content: str, n: int) -> list[QuizQ]:
        payload = _call_json(
            _QUIZ_PROMPT.replace("{n}", str(max(1, n))).replace("{topic}", topic)
                       .replace("{content}", (content or "")[:2000]),
            model=model, provider=provider)
        return _parse_quizq(payload)
    return _fn


# ---------------- Resource search (B-F3, real model; URLs unverified) ----------------

_SEARCH_PROMPT = """你是学习资源推荐器。为主题推荐 {k} 个真实、高质量、公开的复习资源
（大学课程主页 / 经典教材官网 / GitHub 高星仓库或 cheatsheet / 公开题库）。
每条输出 JSON：{"title":..., "url":..., "source_type":..., "provider":..., "year":..., "difficulty":...}
- source_type 必须是之一：course, doc, repo, blog, book, video
- url 必须是你确信真实可访问的 URL（不确定就不要写）；provider：来源机构/网站
- year：年份整数；difficulty：beginner/intermediate/advanced

主题：{topic}

【输出格式】无论主题是中文还是英文，只输出一个 JSON 数组：直接以 [ 开头、以 ] 结尾。
不要 Markdown 标题/列表、不要解释文字、不要 ``` 代码围栏。"""


def _parse_resources(payload):
    from campus.demo_c.types import Resource
    out = []
    for it in (payload if isinstance(payload, list) else []):
        if not isinstance(it, dict):
            continue
        title = str(it.get("title", "")).strip()
        url = str(it.get("url", "")).strip()
        if not title or not url or not url.startswith("http"):
            continue
        try:
            out.append(Resource(
                title=title, url=url,
                source_type=str(it.get("source_type", "doc") or "doc").lower(),
                provider=str(it.get("provider", "") or ""),
                year=it.get("year") or None,
                difficulty=str(it.get("difficulty", "") or ""),
            ))
        except Exception:
            out.append(Resource(title=title, url=url))
    return out


def _parse_markdown_resources(raw: str):
    """Fallback: GLM ignored the JSON contract and returned Markdown (common with
    Chinese topics). Scrape real URLs out of the prose so B-F3 still gets candidates.

    Picks up the nearest preceding heading as each URL's title.
    """
    import re
    from campus.demo_c.types import Resource
    out = []
    seen = set()
    pending_title = None
    for ln in (raw or "").splitlines():
        s = ln.strip()
        mh = re.match(r"#{1,6}\s*\d*\.?\s*(.+)", s)
        if mh:
            pending_title = mh.group(1).strip().rstrip("*:：")
        for url in re.findall(r"https?://[^\s)\]<>]+", s):
            url = url.rstrip(".,;)")
            if url in seen:
                continue
            seen.add(url)
            title = pending_title or url.split("//")[-1].split("/")[0]
            try:
                out.append(Resource(title=title[:80], url=url, source_type="doc"))
            except Exception:
                out.append(Resource(title=title[:80], url=url))
    return out


def make_searcher(model: str = DEFAULT_MODEL, provider: str = DEFAULT_PROVIDER,
                  top_k: int = 6):
    """searcher(topic) -> list[Resource] backed by GLM (URLs NOT yet verified)."""
    def _fn(topic: str):
        prompt = _SEARCH_PROMPT.replace("{k}", str(top_k)).replace("{topic}", topic)
        try:
            raw, rc = ask_llm(prompt, model=model, provider=provider)
        except Exception:
            raw, rc = "", 1
        payload = extract_json(raw) if (rc == 0 and raw) else None
        res = _parse_resources(payload) or _parse_markdown_resources(raw)
        return res if res else default_searcher(topic)   # never empty (B-F3 safe)
    return _fn


# ---------------- convenience runner ----------------

def run_demo_b_live(path: str, exam_date: str, *,
                    free_minutes: int = 300, start_date: Optional[str] = None,
                    topic: Optional[str] = None, slot_minutes: int = 20,
                    model: str = DEFAULT_MODEL, provider: str = DEFAULT_PROVIDER,
                    run_dir: Optional[str] = None):
    """Run Demo B end-to-end with the REAL GLM on all three seams."""
    from campus.demo_b.pipeline import run_demo_b
    return run_demo_b(
        path, exam_date,
        free_minutes=free_minutes, start_date=start_date, topic=topic,
        slot_minutes=slot_minutes, run_dir=run_dir,
        extract_fn=make_extract_fn(model, provider),
        searcher=make_searcher(model, provider),
        quiz_fn=make_quiz_fn(model, provider),
    )


def _main():
    ap = argparse.ArgumentParser(description="Demo B with real GLM (extract/quiz/search).")
    ap.add_argument("path", help="讲义目录")
    ap.add_argument("exam_date", help="考试日 yyyy-mm-dd")
    ap.add_argument("--free", type=int, default=300)
    ap.add_argument("--start", default=None)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--provider", default=DEFAULT_PROVIDER)
    a = ap.parse_args()
    r = run_demo_b_live(a.path, a.exam_date, free_minutes=a.free,
                        start_date=a.start, model=a.model, provider=a.provider)
    print(json.dumps({
        "ok": r.ok, "run_dir": r.run_dir, "kg_nodes": r.kg_nodes,
        "resource_count": r.resource_count, "plan_days": r.plan_days,
        "checks": [{"name": c.name, "passed": c.passed} for c in r.checks],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()
