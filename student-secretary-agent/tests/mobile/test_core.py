"""Mobile push tests (S-MOBILE): Feishu real-path (mocked subprocess) + QQ/WeCom ports."""
import os
import sys
from types import SimpleNamespace

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from campus.mobile import (
    FeishuPusher, QQBotPusher, WeComPusher, push, PushReceipt, PushError,
)


def _cp(rc=0, out="msg-id-123", err=""):
    return SimpleNamespace(returncode=rc, stdout=out, stderr=err)


# ---------------- Feishu (real path, mocked runner) ----------------

def test_feishu_success_command_shape():
    seen = {}

    def runner(cmd, capture_output=True, text=True):
        seen["cmd"] = cmd
        return _cp(0, "ok-token")

    r = FeishuPusher(runner=runner, default_target="oc_91b102abc").send(None, "hello")
    assert r.ok and r.channel == "feishu" and r.target == "oc_91b102abc"
    cmd = seen["cmd"]
    assert "hermes" in cmd[0] and "send" in cmd
    assert any("feishu:oc_91b102abc" in str(c) for c in cmd)   # P5-MOB1
    assert "hello" in cmd


def test_feishu_failure_on_nonzero_rc():
    r = FeishuPusher(runner=lambda *a, **k: _cp(3, "", "boom"),
                    default_target="oc_x").send(None, "hi")
    assert not r.ok and "rc=3" in r.error


def test_feishu_no_target_raises():
    raised = False
    try:
        FeishuPusher(runner=lambda *a, **k: _cp(0)).send(None, "hi")
    except PushError:
        raised = True
    assert raised


def test_feishu_empty_message_failure():
    r = FeishuPusher(runner=lambda *a, **k: _cp(0), default_target="oc_x").send(None, "")
    assert not r.ok and "empty" in r.error


# ---------------- QQ Bot / WeCom (ports + injectable sender) ----------------

def test_qq_no_sender_is_failure_not_raise(monkeypatch):
    # force no real QQ env so the auto-init doesn't pick up real keys
    for k in ("QQ_APP_ID", "QQ_CLIENT_SECRET"):
        monkeypatch.delenv(k, raising=False)
    r = QQBotPusher(sender=None).send("group_1", "hi")
    assert not r.ok and r.channel == "qq" and "configured" in r.error


def test_qq_injected_sender_success():
    calls = {}

    def sender(target, msg):
        calls["args"] = (target, msg)
        return {"ok": True, "message_id": "qq-1"}

    r = QQBotPusher(sender=sender).send("group_1", "hi")
    assert r.ok and r.message_id == "qq-1"
    assert calls["args"] == ("group_1", "hi")


def test_qq_sender_exception_surfaced():
    def bad(target, msg):
        raise RuntimeError("network down")
    r = QQBotPusher(sender=bad).send("g", "hi")
    assert not r.ok and "network down" in r.error


def test_wecom_no_sender_failure_and_injected_success():
    assert not WeComPusher().send(None, "x").ok
    r = WeComPusher(sender=lambda t, m: PushReceipt.success("wecom", t, "wc-9")).send("@all", "go")
    assert r.ok and r.message_id == "wc-9"


# ---------------- dispatcher ----------------

def test_push_dispatch_feishu_with_fake_runner():
    pushers = {"feishu": FeishuPusher(runner=lambda *a, **k: _cp(0), default_target="oc_x")}
    r = push("feishu", "oc_x", "hi", pushers=pushers)
    assert r.ok and r.channel == "feishu"


def test_push_unknown_channel_failure():
    r = push("telegram", None, "hi")
    assert not r.ok and "unknown" in r.error


def test_push_empty_message_failure():
    r = push("qq", None, "", pushers={"qq": QQBotPusher(sender=lambda *a: {"ok": True})})
    assert not r.ok and "empty" in r.error


def test_push_receipt_builders():
    ok = PushReceipt.success("feishu", "oc_x")
    assert ok.ok and ok.message_id
    bad = PushReceipt.failure("qq", "nope")
    assert not bad.ok and bad.error == "nope"
