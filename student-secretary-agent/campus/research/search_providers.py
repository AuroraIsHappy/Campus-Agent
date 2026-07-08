"""Real search providers for research + GitHub trending (Phase 8 Step 6).

Replaces the canned ``example.edu`` / ``github.com/example/`` stub data with
real API calls when keys are configured. Falls back to the deterministic stub
when no key is available (keeps tests hermetic + offline mode working).

Providers:
  - Tavily search (TAVILY_API_KEY): web search for research papers/resources
  - GitHub trending (GITHUB_TOKEN): real GitHub API search for trending repos
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Any, Optional

__all__ = ["search_web", "github_search", "tavily_available", "github_available"]


def tavily_available() -> bool:
    return bool(os.environ.get("TAVILY_API_KEY"))


def github_available() -> bool:
    return bool(os.environ.get("GITHUB_TOKEN"))


def search_web(query: str, *, max_results: int = 5) -> Optional[list[dict[str, Any]]]:
    """Search the web via Tavily API. Returns None if unavailable (caller falls back).

    Each result: {title, url, content, score}.
    """
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        return None
    try:
        body = json.dumps({
            "api_key": key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for r in data.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": (r.get("content") or "")[:500],
                "score": r.get("score", 0),
            })
        return results if results else None
    except Exception:
        return None


def github_search(topic: str, *, language: str = "Python",
                  max_results: int = 5) -> Optional[list[dict[str, Any]]]:
    """Search GitHub for trending repos matching ``topic``. Returns None if unavailable.

    Uses the GitHub Search API (sorted by stars). Each result:
    {name, url, language, stars, reason, description}.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return None
    try:
        q = f"{topic} language:{language}" if language else topic
        url = (f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}"
               f"&sort=stars&order=desc&per_page={max_results}")
        req = urllib.request.Request(url, headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        items = []
        for repo in data.get("items", [])[:max_results]:
            items.append({
                "name": repo.get("full_name", repo.get("name", "")),
                "url": repo.get("html_url", ""),
                "language": repo.get("language", language),
                "stars": repo.get("stargazers_count", 0),
                "description": repo.get("description", ""),
                "reason": f"GitHub 热门项目 ({repo.get('stargazers_count', 0)} ★)",
            })
        return items if items else None
    except Exception:
        return None
