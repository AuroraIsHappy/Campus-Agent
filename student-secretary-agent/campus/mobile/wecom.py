"""WeCom (企业微) pusher (Phase 5 S-MOBILE) -- port + injectable sender.

Mirrors ``qq_bot``: WeCom's official API (CorpID/Secret/AgentID) is user-provisioned,
so the channel is a pure port with an injectable ``sender``. No credentials are
required to import or call it; an unconfigured channel returns a deterministic
failure receipt. Real provisioning steps live in README.
"""
from __future__ import annotations
from typing import Callable, Optional

from campus.mobile.ports import PushReceipt, ReceiptBuilder

__all__ = ["WeComPusher"]

Sender = Callable[[Optional[str], str], object]


class WeComPusher:
    channel = "wecom"

    def __init__(self, sender: Optional[Sender] = None):
        self._sender = sender

    def send(self, target: Optional[str], message: str) -> PushReceipt:
        if not message:
            return PushReceipt.failure(self.channel, "empty message", target or "")
        if self._sender is None:
            return PushReceipt.failure(
                self.channel, "no WeCom sender configured (set CAMPUS_WECOM_CORP_ID/SECRET)",
                target or "")
        try:
            res = self._sender(target, message)
        except Exception as e:
            return PushReceipt.failure(self.channel, f"sender error: {e}", target or "")
        return ReceiptBuilder.from_result(res, self.channel, target or "")
