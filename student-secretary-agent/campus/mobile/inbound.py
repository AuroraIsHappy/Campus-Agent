"""Mobile inbound command channel (Phase 8 — GOAL.md "移动端聊天机器人对话").

Receives a user message from Feishu/QQ, runs it through the agent, formats the
result + proof/explanation, pushes the reply back to the user's channel, and
persists everything to CAMPUS_HOME.

This is the "user sends a command via mobile → agent runs → reply + local
artifacts" loop. The web frontend is NOT needed — the user can interact purely
via Feishu/QQ chat.

Usage from the API::

    POST /mobile/command
    {"message": "帮我生成操作系统 flashcards", "channel": "feishu", "target": "<chat_id>"}

The endpoint calls ``handle_mobile_command`` which:
  1. Runs the agent (``_default_agent_run``) → run record + artifacts
  2. Formats a reply with result summary + proof (artifacts list, source_mode)
  3. Pushes the reply to the user's channel (if push is configured)
  4. Returns the formatted reply + run metadata

For Feishu webhook integration, a ``/mobile/webhook/feishu`` endpoint accepts
the Feishu event format and dispatches to ``handle_mobile_command``.
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

from campus.runtime.stores import ArtifactStore, RunStore

__all__ = ["handle_mobile_command", "format_reply", "push_reply"]


def handle_mobile_command(message: str, *, channel: str = "feishu",
                          target: Optional[str] = None,
                          agent_run_fn=None) -> dict[str, Any]:
    """Process a mobile user command: run agent → format reply → push → persist.

    Returns {ok, reply, run_id, artifacts, pushed}.
    """
    # 1. Run the agent
    if agent_run_fn is None:
        from campus.api.server import _default_agent_run
        from campus.api.types import AgentRunRequest
        result = _default_agent_run(AgentRunRequest(message=message, mode="auto"))
    else:
        result = agent_run_fn(message)

    run_id = result.get("run_id", "")
    status = result.get("status", "")
    error = result.get("error", "")
    artifacts = result.get("artifacts", [])
    multiagent = result.get("multiagent", False)

    # 2. Format the reply with result + proof
    reply = format_reply(message, result)

    # 3. Persist the command log (mobile_commands.json)
    _log_mobile_command(message, channel, target, run_id, status, reply)

    # 4. Push the reply back to the user's channel (if configured)
    pushed = False
    push_error = ""
    if channel and target:
        try:
            pushed, push_error = push_reply(channel, target, reply)
        except Exception as e:
            push_error = str(e)

    return {
        "ok": status != "failed",
        "reply": reply,
        "run_id": run_id,
        "status": status,
        "artifacts": artifacts,
        "multiagent": multiagent,
        "pushed": pushed,
        "push_error": push_error,
        "channel": channel,
        "target": target or "",
    }


def format_reply(message: str, result: dict[str, Any]) -> str:
    """Format the agent result into a readable mobile reply with proof.

    Includes: what was done, the key output, source mode (AI/template), and
    artifact/proof references (file paths under CAMPUS_HOME).
    """
    lines = []
    domain = result.get("domain", "")
    intent = result.get("intent", "")
    status = result.get("status", "")
    artifacts = result.get("artifacts", [])
    error = result.get("error", "")
    multiagent = result.get("multiagent", False)

    # Header
    lines.append(f"📋 任务完成：{domain or '通用'} · {intent}")
    lines.append(f"状态：{'✅ 成功' if status == 'done' else '⚠️ ' + status}")
    if multiagent:
        lines.append("（多智能体协作完成）")

    # Key output: extract from result data
    # The result itself is the run metadata; the actual content is in the
    # run_result.json artifact. Let's read it.
    run_id = result.get("run_id", "")
    if run_id:
        try:
            runs = RunStore()
            artifacts_store = ArtifactStore(runs)
            rec = runs.get(run_id)
            if rec and rec.result:
                content = _extract_content(rec.result)
                if content:
                    lines.append("")
                    lines.append("📝 结果：")
                    lines.append(content[:1500])
                    source_mode = rec.result.get("source_mode", "")
                    if source_mode:
                        is_llm = "llm" in source_mode or "real" in source_mode
                        lines.append(f"\n🤖 来源：{'AI 生成' if is_llm else '模板'} ({source_mode})")
                    elif "real_github" in str(rec.result.get("source_mode", "")):
                        lines.append(f"\n🔍 来源：实时 GitHub API")
        except Exception:
            pass

    # Proof / artifacts
    if artifacts:
        lines.append("")
        lines.append("📁 产物（已保存到本地）：")
        for a in artifacts[:8]:
            name = a.get("name", "") if isinstance(a, dict) else str(a)
            path = a.get("path", "") if isinstance(a, dict) else ""
            lines.append(f"  · {name}" + (f"  → {path}" if path else ""))

    # Error
    if error:
        lines.append("")
        lines.append(f"❌ 错误：{error}")

    lines.append("")
    lines.append("— 你的校园秘书 💬")
    return "\n".join(lines)


def _extract_content(result: dict[str, Any]) -> str:
    """Pull the most useful content from the agent run result dict."""
    # Multi-agent result has 'summary'
    if result.get("summary"):
        return str(result["summary"])
    # Flashcards
    if result.get("flashcards"):
        cards = result["flashcards"]
        return "\n".join(f"Q: {c.get('front','')}\nA: {c.get('back','')}" for c in cards[:5])
    # Quiz questions
    if result.get("questions"):
        return "\n".join(f"Q{i+1}: {q.get('question','')}" for i, q in enumerate(result["questions"][:5]))
    # Jobs
    if result.get("jobs"):
        return "\n".join(f"· {j.get('title','')} @ {j.get('company','')} ({j.get('city','')})" for j in result["jobs"][:5])
    # GitHub items
    if result.get("items"):
        return "\n".join(f"· {g.get('name','')} ★{g.get('stars','')} — {g.get('reason','')}" for g in result["items"][:5])
    # Email
    if result.get("email"):
        return str(result["email"])[:800]
    # Meeting minutes
    if result.get("minutes"):
        m = result["minutes"]
        return f"决议: {', '.join(m.get('decisions',[]))}\n待办: {', '.join(m.get('todo',[]))}"
    # Travel itinerary
    if result.get("itinerary"):
        return "\n".join(f"Day {d.get('day','')}: {d.get('morning','')} / {d.get('afternoon','')}" for d in result["itinerary"][:5])
    # Interview plan
    if result.get("plan"):
        return "\n".join(f"Day {p.get('day','')}: {p.get('focus','')}" for p in result["plan"][:5])
    # Copy
    if result.get("copy"):
        c = result["copy"]
        return f"{c.get('headline','')}\n{c.get('body','')}"
    # Research digest
    if result.get("papers"):
        return "\n".join(f"· {p.get('title','')} ({p.get('year','')})" for p in result["papers"][:5])
    return ""


def push_reply(channel: str, target: str, message: str) -> tuple[bool, str]:
    """Push the reply to the user's mobile channel. Returns (ok, error)."""
    try:
        from campus.mobile.cli import push
        receipt = push(channel, target, message)
        return receipt.ok, receipt.error
    except Exception as e:
        return False, str(e)


def _log_mobile_command(message: str, channel: str, target: Optional[str],
                        run_id: str, status: str, reply: str) -> None:
    """Persist the mobile command + reply to mobile_commands.json."""
    try:
        from campus.runtime.paths import state_dir
        import time
        path = os.path.join(state_dir(), "mobile_commands.json")
        data = []
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        data.append({
            "ts": int(time.time()),
            "channel": channel,
            "target": target or "",
            "message": message[:200],
            "run_id": run_id,
            "status": status,
            "reply_preview": reply[:200],
        })
        data = data[-200:]  # keep last 200
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # never let logging fail the command
