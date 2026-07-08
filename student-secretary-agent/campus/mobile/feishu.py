"""Feishu pusher (Phase 5 S-MOBILE) -- the REAL channel.

Shells out to the already-configured ``hermes send --to feishu:<chat_id>`` CLI
(gateway running separately; memory records the chat id ``oc_91b102…``). The
subprocess runner is injectable so tests assert the command shape + receipt
without spawning hermes or touching the network.

``hermes_cli`` is never imported here -- we drive the CLI binary, which keeps
this module importable with plain Python and decoupled from Hermes internals.
"""
from __future__ import annotations
import os
from typing import Callable, Optional

from campus.mobile.ports import PushReceipt, PushError

__all__ = ["FeishuPusher", "default_feishu_target"]

# Runner signature mirrors subprocess.run(cmd, capture_output, text) -> CompletedProcess.
Runner = Callable[..., object]


def default_feishu_target() -> Optional[str]:
    """Chat id from env (CAMPUS_FEISHU_CHAT_ID) or None if unset."""
    return os.environ.get("CAMPUS_FEISHU_CHAT_ID") or None


class FeishuPusher:
    """Real Feishu delivery via the ``hermes send`` CLI (S-MOBILE main channel)."""

    channel = "feishu"

    def __init__(self, *, runner: Optional[Runner] = None,
                 binary: str = "hermes",
                 default_target: Optional[str] = None):
        self._runner = runner
        self._binary = binary
        self._default_target = default_target if default_target is not None else default_feishu_target()

    def _command(self, target: str, message: str) -> list[str]:
        return [self._binary, "send", "--to", f"feishu:{target}", message]

    def send(self, target: Optional[str], message: str) -> PushReceipt:
        tgt = target or self._default_target
        if not tgt:
            raise PushError("feishu: no target (set CAMPUS_FEISHU_CHAT_ID or pass target)")
        if not message:
            return PushReceipt.failure(self.channel, "empty message", tgt)
        cmd = self._command(tgt, message)
        if self._runner is None:
            import subprocess  # real path; lazy so the module stays hermetic
            cp = subprocess.run(cmd, capture_output=True, text=True)
        else:
            cp = self._runner(cmd, capture_output=True, text=True)
        rc = getattr(cp, "returncode", 1)
        out = (getattr(cp, "stdout", "") or "")
        if rc == 0:
            return PushReceipt.success(self.channel, tgt,
                                       message_id=_first_token(out) or "feishu-sent")
        err = (getattr(cp, "stderr", "") or str(out))[:200]
        return PushReceipt.failure(self.channel, f"hermes rc={rc}: {err}", tgt)


def _first_token(text: str) -> str:
    t = (text or "").strip().splitlines()
    return t[0][:40] if t else ""
