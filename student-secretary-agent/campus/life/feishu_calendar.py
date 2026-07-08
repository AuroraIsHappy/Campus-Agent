"""Feishu (Lark) Calendar API client (Phase 9 — GOAL.md 飞书日历同步).

Creates calendar events in the user's Feishu calendar so generated study/review
plans land where the user actually looks. Uses the official Open API:

1. ``tenant_access_token`` — POST ``/auth/v3/tenant_access_token/internal`` with
   ``app_id`` + ``app_secret`` (cached until expiry).
2. Create event — POST ``/calendar/v1/calendars/{calendar_id}/events`` with
   ``Authorization: Bearer <tenant_access_token>``.

Consumes the previously-dead ``FEISHU_APP_ID`` / ``FEISHU_APP_SECRET`` /
``FEISHU_DOMAIN`` env vars + a new ``FEISHU_CALENDAR_ID``.

Mirrors ``campus/mobile/qq_bot_api.py``'s urllib + injectable + never-raise
convention. No MCP — direct REST, consistent with Notion/Zotero/GitHub patterns.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any, Optional

__all__ = ["FeishuCalendarSyncer", "status", "_env"]

_DEFAULT_DOMAIN = "https://open.feishu.cn"


def _env(key: str) -> str:
    return os.environ.get(key, "")


def status() -> dict[str, Any]:
    """Report Feishu Calendar config readiness (no network call)."""
    app_id = _env("FEISHU_APP_ID")
    secret = _env("FEISHU_APP_SECRET")
    cal_id = _env("FEISHU_CALENDAR_ID")
    return {
        "ok": bool(app_id and secret and cal_id),
        "app_id_configured": bool(app_id),
        "secret_configured": bool(secret),
        "calendar_id_configured": bool(cal_id),
        "mode": "feishu_calendar_ready" if app_id and secret and cal_id else "not_configured",
    }


class FeishuCalendarSyncer:
    """Feishu Calendar event creator (urllib, never raises on config errors)."""

    def __init__(self, *, app_id: str = "", app_secret: str = "",
                 calendar_id: str = "", domain: str = "",
                 http_timeout: int = 20) -> None:
        self.app_id = app_id or _env("FEISHU_APP_ID")
        self.app_secret = app_secret or _env("FEISHU_APP_SECRET")
        self.calendar_id = calendar_id or _env("FEISHU_CALENDAR_ID")
        # FEISHU_DOMAIN may be a connection-mode label (e.g. "feishu"/"websocket")
        # rather than a URL — only use it if it looks like an http(s) URL.
        domain_val = domain or _env("FEISHU_DOMAIN") or ""
        if domain_val and not domain_val.startswith("http"):
            domain_val = ""
        self.domain = (domain_val or _DEFAULT_DOMAIN).rstrip("/")
        self.timeout = http_timeout
        self._token: str = ""
        self._token_expiry: float = 0

    # ---- token ----
    def _tenant_access_token(self) -> str:
        """Fetch + cache the tenant_access_token until expiry."""
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        body = json.dumps({"app_id": self.app_id,
                           "app_secret": self.app_secret}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.domain}/open-apis/auth/v3/tenant_access_token/internal",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if payload.get("code") != 0:
            raise RuntimeError(f"Feishu token error: {payload.get('msg', '')}")
        self._token = payload["tenant_access_token"]
        self._token_expiry = time.time() + payload.get("expire", 7200)
        return self._token

    # ---- public API ----
    def health_check(self) -> dict[str, Any]:
        """Verify credentials by fetching a token. Returns {ok, configured, error}."""
        if not (self.app_id and self.app_secret and self.calendar_id):
            return {"ok": False, "configured": False,
                    "error": "FEISHU_APP_ID/SECRET/CALENDAR_ID not set"}
        try:
            self._tenant_access_token()
            return {"ok": True, "configured": True, "error": ""}
        except Exception as e:
            return {"ok": False, "configured": True, "error": str(e)[:200]}

    def create_event(self, *, summary: str, start_ts: int, end_ts: int,
                     description: str = "", location: str = "",
                     recurrence: Optional[str] = None) -> dict[str, Any]:
        """Create a calendar event. Returns {ok, event_id, error}.

        ``start_ts``/``end_ts`` are Unix timestamps (seconds).
        ``recurrence`` is an RFC 5545 RRULE string (e.g. ``RRULE:FREQ=WEEKLY``)
        or None for a one-off.
        """
        if not (self.app_id and self.app_secret and self.calendar_id):
            return {"ok": False, "event_id": "", "error": "not configured"}
        try:
            token = self._tenant_access_token()
            body: dict[str, Any] = {
                "summary": summary[:200],
                "description": description[:1000],
                "start_time": {"timestamp": str(start_ts)},
                "end_time": {"timestamp": str(end_ts)},
            }
            if location:
                body["location"] = {"name": location[:200]}
            if recurrence:
                body["recurrence"] = [recurrence]
            req = urllib.request.Request(
                f"{self.domain}/open-apis/calendar/v1/calendars/{self.calendar_id}/events",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            if payload.get("code") != 0:
                return {"ok": False, "event_id": "",
                        "error": f"Feishu: {payload.get('msg', '')}"}
            event = payload.get("data", {}).get("event", {})
            return {"ok": True, "event_id": event.get("event_id", ""),
                    "error": ""}
        except Exception as e:
            return {"ok": False, "event_id": "", "error": str(e)[:200]}


def rrule_to_rfc5545(rrule: Optional[str]) -> Optional[str]:
    """Map the local simplified RRULE tokens (DAILY/WEEKLY) to RFC 5545.

    The local ``calendar_store`` uses ``"DAILY"``/``"WEEKLY"`` tokens; Feishu
    expects full RFC 5545 strings like ``RRULE:FREQ=WEEKLY``.
    """
    if not rrule:
        return None
    r = rrule.strip().upper()
    if r in ("DAILY", "WEEKLY", "MONTHLY", "YEARLY"):
        return f"RRULE:FREQ={r}"
    if r.startswith("RRULE:"):
        return r
    return None
