"""Push-channel ports for mobile delivery (Phase 5 S-MOBILE).

``PushPort`` is the vendor-neutral seam every channel implements. The receipt
captures enough to assert delivery in tests and to surface failures to the API.

Design (architecture §C4②): the real Feishu path shells out to the existing
``hermes send`` CLI (gateway already configured; memory has the chat id);
QQ Bot / WeCom are pure ports with an injectable ``sender`` so they work with
no credentials (real provisioning is a documented manual step, not a code dep).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

__all__ = ["PushReceipt", "PushPort", "PushError", "ReceiptBuilder"]

_OK_DEFAULT = "ok"


@dataclass
class PushReceipt:
    """Outcome of one push attempt (mirrors a delivery confirmation)."""
    ok: bool
    channel: str
    target: str = ""
    message_id: str = ""
    error: str = ""

    @classmethod
    def success(cls, channel: str, target: str = "", message_id: str = "") -> "PushReceipt":
        return cls(ok=True, channel=channel, target=target,
                   message_id=message_id or f"{channel}-{_OK_DEFAULT}")

    @classmethod
    def failure(cls, channel: str, error: str, target: str = "") -> "PushReceipt":
        return cls(ok=False, channel=channel, target=target, error=error)


class PushError(Exception):
    """Raised only when a channel is misconfigured (missing target, unknown channel)."""


@runtime_checkable
class PushPort(Protocol):
    """send(target, message) -> PushReceipt. Real + stub channels both fit."""
    channel: str

    def send(self, target: Optional[str], message: str) -> PushReceipt: ...


class ReceiptBuilder:
    """Tiny helper for injectable senders that return raw dicts/tuples."""

    @staticmethod
    def from_result(result, channel: str, target: str) -> PushReceipt:
        if isinstance(result, PushReceipt):
            return result
        if isinstance(result, dict):
            return PushReceipt(ok=bool(result.get("ok", False)),
                               channel=channel, target=target,
                               message_id=str(result.get("message_id", "")),
                               error=str(result.get("error", "")))
        return PushReceipt.success(channel, target) if result else PushReceipt.failure(channel, "empty")
