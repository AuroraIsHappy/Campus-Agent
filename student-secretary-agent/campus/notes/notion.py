"""Notion sync facade with a local Markdown mirror fallback."""
from __future__ import annotations

import os
import re
import time
import json
import urllib.request

def _base() -> str:
    return os.path.join(os.path.abspath(os.path.expanduser(os.environ.get("CAMPUS_HOME", "~/.campus"))), "notes", "research")


def status() -> dict:
    token = bool(os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_TOKEN"))
    db = os.environ.get("NOTION_RESEARCH_DATA_SOURCE_ID") or os.environ.get("NOTION_RESEARCH_DATABASE_ID") or ""
    return {
        "ok": token and bool(db),
        "token_configured": token,
        "database_configured": bool(db),
        "mode": "notion_ready" if token and db else "local_only",
        "local_mirror_dir": _base(),
    }


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:50] or "research-note"


def _markdown_from_digest(digest: dict) -> str:
    topic = (digest.get("topic") or {}).get("title") or digest.get("topic_id") or "Research"
    lines = [f"# {topic}", "", digest.get("summary", ""), "", "## Papers"]
    for p in digest.get("papers", []):
        lines += [
            "",
            f"### {p.get('title', 'Untitled')}",
            f"- URL: {p.get('url', '')}",
            f"- Year: {p.get('year', '')}",
            f"- Score: {p.get('score', '')}",
            f"- Notes: {p.get('abstract', '')}",
        ]
    lines += ["", "## Questions"]
    lines += [f"- {q}" for q in digest.get("questions", [])]
    return "\n".join(lines).strip() + "\n"


def sync_digest(digest: dict, mode: str = "local") -> dict:
    base = _base()
    os.makedirs(base, exist_ok=True)
    topic = (digest.get("topic") or {}).get("title") or digest.get("topic_id") or "research"
    path = os.path.join(base, f"{_slug(topic)}-{int(time.time())}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(_markdown_from_digest(digest))

    st = status()
    if mode == "notion" and not st["ok"]:
        return {
            "ok": False,
            "local_path": path,
            "notion_ok": False,
            "error": "Notion token/database not configured; wrote local Markdown mirror.",
            "status": st,
        }
    notion_page = ""
    notion_error = ""
    if mode == "notion" and st["ok"]:
        try:
            notion_page = _create_notion_page(digest)
        except Exception as e:
            notion_error = str(e)
    return {
        "ok": True,
        "local_path": path,
        "notion_ok": bool(notion_page),
        "notion_page": notion_page,
        "error": notion_error,
        "status": st,
    }


def _create_notion_page(digest: dict) -> str:
    token = os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_TOKEN") or ""
    db = os.environ.get("NOTION_RESEARCH_DATA_SOURCE_ID") or os.environ.get("NOTION_RESEARCH_DATABASE_ID") or ""
    title = (digest.get("topic") or {}).get("title") or digest.get("topic_id") or "Research digest"
    summary = digest.get("summary", "")
    body = {
        "parent": {"database_id": db},
        "properties": {
            "Name": {"title": [{"text": {"content": title[:2000]}}]},
            "Summary": {"rich_text": [{"text": {"content": summary[:2000]}}]},
        },
        "children": [
            {"object": "block", "type": "paragraph",
             "paragraph": {"rich_text": [{"type": "text", "text": {"content": summary[:2000]}}]}},
        ],
    }
    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("url", "")
