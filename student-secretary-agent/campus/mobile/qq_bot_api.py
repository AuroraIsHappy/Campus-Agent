"""Real QQ Bot API client (Phase 8 Step 5).

Implements the official q.qq.com API: get an access_token via AppID/Secret,
then send a message to a channel/group. Used as the default ``sender`` for
``QQBotPusher`` when ``QQ_APP_ID`` + ``QQ_CLIENT_SECRET`` are configured.

If credentials are missing or the API call fails, returns a deterministic
failure receipt (never raises) so the pipeline stays robust.

API docs: https://bot.q.qq.com/wiki/develop/api/
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from typing import Optional

from campus.mobile.ports import PushReceipt

__all__ = ["QQBotAPIClient", "default_qq_sender"]

_QQ_TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"
_QQ_MSG_URL = "https://api.sgroup.qq.com"


class QQBotAPIClient:
    """Minimal QQ Bot API client: auth + send message."""

    def __init__(self, *, app_id: str = "", secret: str = "",
                 channel: str = "", http_timeout: int = 15) -> None:
        self.app_id = app_id or os.environ.get("QQ_APP_ID", "")
        self.secret = secret or os.environ.get("QQ_CLIENT_SECRET", "")
        self.channel = channel or os.environ.get("QQBOT_HOME_CHANNEL", "")
        self.timeout = http_timeout
        self._token: str = ""
        self._token_expires: int = 0

    def _get_token(self) -> Optional[str]:
        """Fetch an access_token via the QQ Bot API. Cached until expiry."""
        if not self.app_id or not self.secret:
            return None
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        body = json.dumps({"appId": self.app_id, "clientSecret": self.secret}).encode("utf-8")
        req = urllib.request.Request(
            _QQ_TOKEN_URL, data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            self._token = data.get("access_token", "")
            expires_in = int(data.get("expires_in", 7200))
            self._token_expires = int(time.time()) + expires_in
            return self._token or None
        except Exception:
            return None

    def send(self, target: Optional[str], message: str) -> PushReceipt:
        """Send a message to a QQ channel/group. Returns a PushReceipt."""
        tgt = target or self.channel
        if not tgt:
            return PushReceipt.failure("qq", "no target (set QQBOT_HOME_CHANNEL or pass target)", "")
        if not message:
            return PushReceipt.failure("qq", "empty message", tgt)
        token = self._get_token()
        if not token:
            return PushReceipt.failure("qq", "auth failed (check QQ_APP_ID/QQ_CLIENT_SECRET)", tgt)
        # Send to channel (C2C / group / channel depending on target format)
        # Target format: "channel:xxx" (channel message) or "group:xxx" (group)
        try:
            if tgt.startswith("channel:"):
                url = f"{_QQ_MSG_URL}/channels/{tgt[8:]}/messages"
                payload = {"content": message}
            elif tgt.startswith("group:"):
                url = f"{_QQ_MSG_URL}/v2/groups/{tgt[6:]}/messages"
                payload = {"content": message, "msg_type": 0}
            else:
                # default: treat as channel id
                url = f"{_QQ_MSG_URL}/channels/{tgt}/messages"
                payload = {"content": message}
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, data=body,
                headers={"Authorization": f"QQBot {token}",
                         "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
            msg_id = resp_data.get("id", "") or "qq-sent"
            return PushReceipt.success("qq", tgt, message_id=msg_id)
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8")[:200]
            except Exception:
                pass
            return PushReceipt.failure("qq", f"HTTP {e.code}: {err_body}", tgt)
        except Exception as e:
            return PushReceipt.failure("qq", str(e)[:200], tgt)

    def health_check(self) -> dict:
        """Check if the QQ Bot is configured and can authenticate."""
        if not self.app_id or not self.secret:
            return {"ok": False, "configured": False,
                    "error": "QQ_APP_ID/QQ_CLIENT_SECRET not set"}
        token = self._get_token()
        return {"ok": bool(token), "configured": True,
                "channel": self.channel or "(not set)",
                "error": "" if token else "auth failed"}


def default_qq_sender():
    """Factory: returns a QQBotAPIClient if configured, else None.

    Skips auto-init during tests (CAMPUS_HOME under .campus-test) so unit tests
    that expect no-sender behavior stay deterministic.
    """
    # test isolation: don't auto-init a real sender in test mode
    import os
    home = os.environ.get("CAMPUS_HOME", "")
    if ".campus-test" in home or ".campus-e2e" in home or ".campus-frtend" in home:
        return None
    client = QQBotAPIClient()
    if client.app_id and client.secret:
        return client
    return None
