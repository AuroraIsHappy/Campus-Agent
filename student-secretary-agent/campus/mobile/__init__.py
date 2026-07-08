"""Mobile push channels (Phase 5 S-MOBILE).

- FeishuPusher: REAL delivery via ``hermes send --to feishu:<id>`` subprocess.
- QQBotPusher / WeComPusher: pure ports + injectable sender (creds = manual).
- cli.push(channel, target, message): dispatcher used by the API /push route.

All channels fit ``PushPort`` and return ``PushReceipt``. Deterministic in
tests via injected runner/sender (no Hermes, no network, no credentials).
"""
from campus.mobile.ports import PushReceipt, PushPort, PushError
from campus.mobile.feishu import FeishuPusher
from campus.mobile.qq_bot import QQBotPusher
from campus.mobile.wecom import WeComPusher
from campus.mobile.cli import push, CHANNELS

__all__ = [
    "PushReceipt", "PushPort", "PushError",
    "FeishuPusher", "QQBotPusher", "WeComPusher",
    "push", "CHANNELS",
]
