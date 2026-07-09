"""Lightweight research-paper tracker used by the API and frontend demo."""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, asdict, field

def _base() -> str:
    return os.path.join(os.path.abspath(os.path.expanduser(os.environ.get("CAMPUS_HOME", "~/.campus"))), "research")


def _topics_path() -> str:
    return os.path.join(_base(), "topics.json")


def _runs_path() -> str:
    return os.path.join(_base(), "runs.json")


@dataclass
class ResearchTopic:
    id: str
    title: str
    query: str
    keywords: list[str] = field(default_factory=list)
    cadence: str = "daily"
    created_at: int = 0


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "topic"


def _read(path: str, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_topics() -> list[dict]:
    return _read(_topics_path(), [])


def add_topic(title: str, query: str, keywords: list[str] | None = None, cadence: str = "daily") -> dict:
    now = int(time.time())
    topic = ResearchTopic(
        id=f"{_slug(title or query)}-{now}",
        title=title or query,
        query=query or title,
        keywords=keywords or [],
        cadence=cadence,
        created_at=now,
    )
    topics = list_topics()
    topics.append(asdict(topic))
    _write(_topics_path(), topics)
    return {"ok": True, "topic": asdict(topic)}


def _offline_papers(topic: dict) -> list[dict]:
    q = topic.get("query") or topic.get("title") or "research"
    return [
        {
            "title": f"{q}: A Practical Survey",
            "url": "https://arxiv.org/abs/0000.00001",
            "authors": ["Offline Demo"],
            "year": 2026,
            "venue": "arXiv",
            "abstract": f"Survey-style overview for {q}, useful as a first reading map.",
            "source": "offline",
            "score": 0.91,
            "reasons": ["主题匹配", "适合快速建立背景"],
        },
        {
            "title": f"Recent Methods for {q}",
            "url": "https://arxiv.org/abs/0000.00002",
            "authors": ["Offline Demo"],
            "year": 2025,
            "venue": "arXiv",
            "abstract": f"Method-focused paper candidates around {q}.",
            "source": "offline",
            "score": 0.86,
            "reasons": ["方法导向", "便于整理笔记"],
        },
    ]


def _real_papers(topic: dict) -> tuple[list[dict], str]:
    """Search for real papers via Tavily web search (Phase 8 Step 6).

    Falls back to the skill-adapter path if Tavily isn't configured.
    """
    q = topic.get("query") or topic.get("title") or "research"
    # Phase 8: try real web search first
    try:
        from campus.research.search_providers import search_web, tavily_available
        if tavily_available():
            results = search_web(f"{q} 论文 paper research", max_results=6)
            if results:
                papers = []
                for r in results:
                    papers.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "year": 2024,
                        "score": round(r.get("score", 0.5) * 10, 1),
                        "abstract": (r.get("content") or "")[:300],
                        "authors": ["(web search)"],
                        "source": "tavily",
                        "reasons": ["来自 Tavily 实时网络搜索"],
                    })
                return papers, "tavily"
    except Exception as e:
        pass
    # fallback: check for vendored research skills (v1 adapter)
    try:
        from campus.skills.registry import audit
        st = audit()
        available = set(st.get("vendor", [])) | set(st.get("installed", [])) | set(st.get("campus", []))
        for name in ("academic-search", "read-arxiv-paper", "academic-researcher", "web-access"):
            if name in available:
                papers = _offline_papers(topic)
                for p in papers:
                    p["source"] = name
                return papers, f"skill_adapter:{name}"
    except Exception:
        pass
    return [], "no search provider available (set TAVILY_API_KEY for real search)"


def refresh_topic(topic_id: str, mode: str = "auto") -> dict:
    topics = list_topics()
    topic = next((t for t in topics if t.get("id") == topic_id), None)
    if topic is None:
        return {"ok": False, "error": "topic not found"}
    requested = (mode or "offline").lower()
    source_error = ""
    source_mode = "offline"
    papers = _offline_papers(topic)
    if requested in {"real", "auto"}:
        real_papers, source_error = _real_papers(topic)
        if real_papers:
            papers = real_papers
            source_mode = "real"
        else:
            source_mode = "fallback_offline"
    digest = {
        "ok": True,
        "mode": requested,
        "source_mode": source_mode,
        "source_error": source_error,
        "topic_id": topic_id,
        "topic": topic,
        "summary": f"本次为 {topic.get('title')} 找到 {len(papers)} 篇候选论文，建议先读综述再读方法论文。",
        "papers": papers,
        "questions": [
            "这篇论文解决的核心问题是什么？",
            "方法和已有工作相比新增了什么假设？",
            "哪些结论可以转化成你的研究笔记或实验计划？",
        ],
        "created_at": int(time.time()),
    }
    try:
        from campus.notes import notion
        note = notion.sync_digest(digest, "local")
        digest["note_path"] = note.get("local_path", "")
    except Exception as e:
        digest["note_path"] = ""
        digest["note_error"] = str(e)
    runs = _read(_runs_path(), [])
    runs.append(digest)
    _write(_runs_path(), runs[-50:])
    return digest


def list_runs() -> list[dict]:
    return _read(_runs_path(), [])
