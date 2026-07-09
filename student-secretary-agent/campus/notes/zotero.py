"""Zotero Web API client (Phase 9 — GOAL.md 文献管理).

Real Zotero REST integration using the user's API key (from ``.hermes/.env``):
``ZOTERO_USER_ID`` + ``ZOTERO_API_KEY``. Lets the agent store found papers into
the user's Zotero library and search it — closing the GOAL.md "文献管理" gap.

API reference: https://www.zotero.org/support/dev/web_api/v3
- Auth: ``Zotero-API-Key: <key>`` header.
- Create items: ``POST /users/<id>/items`` with a JSON **array** of item templates.
- Search/list: ``GET /users/<id>/items?q=<query>&limit=<n>``.

Mirrors the codebase's urllib + never-raise + injectable-HTTP convention (same
shape as ``campus/notes/notion.py`` and ``campus/research/search_providers.py``).
No MCP — the project is pure FastAPI; direct REST fits the existing pattern.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any, Optional

__all__ = ["ZoteroClient", "status", "sync_papers", "search", "_env"]

_API_BASE = "https://api.zotero.org"


def _env(key: str) -> str:
    return os.environ.get(key, "")


def _user_id() -> str:
    return _env("ZOTERO_USER_ID")


def _api_key() -> str:
    return _env("ZOTERO_API_KEY")


def status() -> dict[str, Any]:
    """Report Zotero config readiness (no network call)."""
    uid = _user_id()
    key = _api_key()
    return {
        "ok": bool(uid and key),
        "user_id_configured": bool(uid),
        "api_key_configured": bool(key),
        "mode": "zotero_ready" if uid and key else "not_configured",
    }


class ZoteroClient:
    """Minimal Zotero Web API client (urllib, never raises on config errors)."""

    def __init__(self, *, user_id: str = "", api_key: str = "",
                 http_timeout: int = 20) -> None:
        self.user_id = user_id or _user_id()
        self.api_key = api_key or _api_key()
        self.timeout = http_timeout

    # ---- low-level HTTP ----
    def _request(self, method: str, path: str, body: Any = None,
                 params: Optional[dict] = None) -> tuple[int, Any]:
        url = f"{_API_BASE}/users/{self.user_id}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={
                "Zotero-API-Key": self.api_key,
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode("utf-8")
            code = resp.status
        payload = json.loads(raw) if raw else None
        return code, payload

    # ---- public API ----
    def health_check(self) -> dict[str, Any]:
        """Verify credentials by fetching one item. Returns {ok, configured, error}."""
        if not (self.user_id and self.api_key):
            return {"ok": False, "configured": False,
                    "error": "ZOTERO_USER_ID/ZOTERO_API_KEY not set"}
        try:
            code, _payload = self._request("GET", "/items",
                                           params={"limit": 1, "format": "json"})
            return {"ok": code == 200, "configured": True,
                    "status_code": code, "error": "" if code == 200 else f"HTTP {code}"}
        except Exception as e:
            return {"ok": False, "configured": True, "error": str(e)[:200]}

    def search(self, query: str = "", limit: int = 10) -> dict[str, Any]:
        """Search the user's Zotero library. Returns {ok, items, error}."""
        if not (self.user_id and self.api_key):
            return {"ok": False, "items": [], "error": "not configured"}
        try:
            params = {"limit": min(limit, 100), "format": "json"}
            if query:
                params["q"] = query
            code, payload = self._request("GET", "/items", params=params)
            if code != 200:
                return {"ok": False, "items": [], "error": f"HTTP {code}"}
            items = []
            for entry in (payload or [])[:limit]:
                d = entry.get("data", {})
                items.append({
                    "key": entry.get("key", ""),
                    "title": d.get("title", ""),
                    "itemType": d.get("itemType", ""),
                    "url": d.get("url", ""),
                    "date": d.get("date", ""),
                    "creators": [c.get("name", "") or
                                 f"{c.get('firstName','')} {c.get('lastName','')}".strip()
                                 for c in d.get("creators", [])],
                    "abstractNote": d.get("abstractNote", "")[:300],
                })
            return {"ok": True, "items": items, "count": len(items)}
        except Exception as e:
            return {"ok": False, "items": [], "error": str(e)[:200]}

    def create_items(self, papers: list[dict[str, Any]]) -> dict[str, Any]:
        """Create Zotero items from paper dicts. Returns {ok, created, error}.

        Paper dict fields (from research tracker): title, url, year, abstract,
        authors, venue. Mapped to Zotero itemTemplate (journalArticle / webpage).
        """
        if not (self.user_id and self.api_key):
            return {"ok": False, "created": 0, "error": "not configured"}
        if not papers:
            return {"ok": True, "created": 0, "error": ""}
        templates = [self._paper_to_template(p) for p in papers]
        try:
            # Zotero expects an array; returns an array of {key, success} dicts
            code, payload = self._request("POST", "/items", body=templates)
            if code not in (200, 201):
                return {"ok": False, "created": 0,
                        "error": f"HTTP {code}: {str(payload)[:200]}"}
            # success response: {"success": {...}, "success_codes": {...}, "unchanged":{}, "failed":{}}
            success = (payload or {}).get("success", {}) if isinstance(payload, dict) else {}
            created = len(success) if isinstance(success, dict) else int(bool(success))
            failed = (payload or {}).get("failed", {}) if isinstance(payload, dict) else {}
            return {"ok": created > 0, "created": created,
                    "total": len(templates),
                    "failed": len(failed) if isinstance(failed, dict) else 0,
                    "keys": list(success.keys()) if isinstance(success, dict) else [],
                    "error": "" if not failed else f"{len(failed)} failed"}
        except Exception as e:
            return {"ok": False, "created": 0, "error": str(e)[:200]}

    @staticmethod
    def _paper_to_template(paper: dict[str, Any]) -> dict[str, Any]:
        """Map a research-tracker paper dict to a Zotero itemTemplate."""
        url = paper.get("url", "") or ""
        # web pages with no venue → webpage; otherwise journalArticle
        item_type = "journalArticle"
        if url and not paper.get("venue"):
            item_type = "webpage"
        year = paper.get("year")
        date = str(year) if year else ""
        authors = paper.get("authors") or []
        creators = []
        for a in authors[:10]:
            if isinstance(a, str):
                # placeholder authors → single-name creator
                creators.append({"creatorType": "author", "name": a})
            elif isinstance(a, dict):
                creators.append({"creatorType": "author",
                                 "firstName": a.get("firstName", ""),
                                 "lastName": a.get("lastName", a.get("name", ""))})
        if not creators:
            creators = [{"creatorType": "author", "name": "(unknown)"}]
        template = {
            "itemType": item_type,
            "title": paper.get("title", "Untitled"),
            "creators": creators,
            "abstractNote": (paper.get("abstract", "") or "")[:3000],
            "url": url,
            "date": date,
            "tags": [{"tag": t} for t in paper.get("reasons", [])[:5]],
        }
        venue = paper.get("venue")
        if venue and item_type == "journalArticle":
            template["publicationTitle"] = venue
        return template


def sync_papers(papers: list[dict[str, Any]], mode: str = "local") -> dict[str, Any]:
    """Facade: store papers to Zotero (+ local mirror). Mirrors notion.sync_digest.

    ``mode``: ``"local"`` writes a Markdown mirror only; ``"zotero"`` also pushes
    to the Zotero library.
    Returns ``{ok, created, local_path, zotero_ok, error, status}``.
    """
    from campus.notes.notion import _base, _slug
    import time

    # local mirror (reuse the research notes dir)
    base = _base()
    os.makedirs(base, exist_ok=True)
    topic = papers[0].get("title", "papers")[:40] if papers else "papers"
    local_path = os.path.join(base, f"{_slug(topic)}-zotero-{int(time.time())}.md")
    lines = [f"# Papers to Zotero ({len(papers)})", ""]
    for p in papers:
        lines.append(f"- {p.get('title', '?')}  ({p.get('url', '')})")
    with open(local_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    st = status()
    if mode != "zotero" or not st["ok"]:
        return {"ok": True, "created": 0, "local_path": local_path,
                "zotero_ok": False,
                "error": "" if mode == "local" else "Zotero not configured; local mirror only.",
                "status": st}

    client = ZoteroClient()
    result = client.create_items(papers)
    return {"ok": result["ok"], "created": result.get("created", 0),
            "local_path": local_path, "zotero_ok": result["ok"],
            "error": result.get("error", ""), "status": st,
            "keys": result.get("keys", [])}


def search(query: str = "", limit: int = 10) -> dict[str, Any]:
    """Search the user's Zotero library (thin wrapper)."""
    st = status()
    if not st["ok"]:
        return {"ok": False, "items": [], "error": "not configured", "status": st}
    return ZoteroClient().search(query, limit)
