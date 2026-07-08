"""QQ Bot pusher (Phase 5 S-MOBILE) -- port + injectable sender.

QQ Bot uses the official q.qq.com API (AppID/Secret) which the user provisions
manually. This module is therefore a pure port: the actual API call is an
injectable ``sender`` callable. With no sender configured, ``send`` returns a
deterministic failure receipt (it never raises and never needs credentials),
so the pipeline/tests stay hermetic. Real provisioning is documented in README.
"""
from __future__ import annotations
from typing import Callable, Optional

from campus.mobile.ports import PushReceipt, PushError, ReceiptBuilder

__all__ = ["QQBotPusher"]

# sender(target, message) -> PushReceipt | dict | truthy
Sender = Callable[[Optional[str], str], object]


class QQBotPusher:
    channel = "qq"

    def __init__(self, sender: Optional[Sender] = None):
        self._sender = sender

    def send(self, target: Optional[str], message: str) -> PushReceipt:
        if not message:
            return PushReceipt.failure(self.channel, "empty message", target or "")
        if self._sender is None:
            return PushReceipt.failure(
                self.channel, "no QQ Bot sender configured (set CAMPUS_QQ_APP_ID/SECRET)",
                target or "")
        try:
            res = self._sender(target, message)
        except Exception as e:  # sender blew up -> surface, don't crash the pipeline
            return PushReceipt.failure(self.channel, f"sender error: {e}", target or "")
        return ReceiptBuilder.from_result(res, self.channel, target or "")
