"""Mobile push dispatcher (Phase 5 S-MOBILE).

``push(channel, target, message)`` routes to the right ``PushPort`` channel.
Used by ``campus.api.server`` ``/push``. Channels can be overridden per call for
tests (inject fake pushers) so dispatch is fully deterministic.
"""
from __future__ import annotations
from typing import Optional

from campus.mobile.ports import PushReceipt, PushError
from campus.mobile.feishu import FeishuPusher
from campus.mobile.qq_bot import QQBotPusher
from campus.mobile.wecom import WeComPusher

__all__ = ["CHANNELS", "push", "get_pusher"]

# channel name -> pusher factory (no-arg construction uses defaults/env)
CHANNELS = {
    "feishu": FeishuPusher,
    "qq": QQBotPusher,
    "wecom": WeComPusher,
    "qq_bot": QQBotPusher,
    "lark": FeishuPusher,
}

# module-level singletons so config (e.g. injected senders) can persist once set
_INSTANCES: dict[str, object] = {}


def get_pusher(channel: str, *, pushers: Optional[dict] = None) -> object:
    """Return the pusher for ``channel``; caches default instances."""
    cls = CHANNELS.get((channel or "").strip())
    if cls is None:
        raise PushError(f"unknown channel: {channel!r} (have {sorted(CHANNELS)})")
    if pushers is not None:
        inst = pushers.get(channel)
        if inst is not None:
            return inst
    if channel not in _INSTANCES:
        _INSTANCES[channel] = cls()
    return _INSTANCES[channel]


def push(channel: str, target: Optional[str], message: str,
         *, pushers: Optional[dict] = None) -> PushReceipt:
    """Send ``message`` via ``channel``. Returns a PushReceipt (never raises)."""
    try:
        p = get_pusher(channel, pushers=pushers)
        return p.send(target, message)
    except PushError as e:
        return PushReceipt.failure(channel or "?", str(e), target or "")
