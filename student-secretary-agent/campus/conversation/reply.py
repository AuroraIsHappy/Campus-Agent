"""Compose a natural-language assistant reply from a structured agent run.

This is the bridge that turns ``/agent/run``'s structured result (domain
metadata + ``run_result.json`` content) into a conversational reply, styled by
the user's persona (费曼/鲁迅/default). It is the core of the chat-first
frontend: the user chats in Feishu-mobile style and gets a human reply, not a
row of metric chips.

Reuses (no duplication):
- ``campus.mobile.inbound._extract_content`` — pulls the deliverable text from
  a run result dict (flashcards/questions/jobs/items/...).
- ``campus.personas.loader.select`` / ``apply_to_prompt`` — persona styling
  (this is the first real consumer of the persona layer).
- ``campus.runtime.llm_turn.ask_llm`` — the proven GLM oneshot primitive.
- ``campus.mobile.inbound.format_reply`` — offline fallback when no LLM.

Clarification: when the agent result indicates ambiguity (e.g. a fuzzy lecture
path with multiple candidates), the composer surfaces it as a question rather
than silently picking.
"""
from __future__ import annotations
import json
from typing import Any, Optional

__all__ = ["compose_reply", "format_history", "resolve_persona_name"]


def resolve_persona_name(req_persona: str = "") -> str:
    """Resolve the active persona name.

    Priority: explicit request → onboarding profile in memory PREFERENCES → default.
    """
    if req_persona and req_persona.strip():
        return req_persona.strip().lower()
    try:
        from campus.memory.json_store import JsonFileStore
        from campus.memory.types import PREFERENCES
        rec = JsonFileStore().get(PREFERENCES, "onboarding_profile")
        if rec and rec.metadata:
            name = rec.metadata.get("persona", "")
            if name:
                return name.lower()
    except Exception:
        pass
    return "default"


def format_history(history: list[dict[str, Any]], max_turns: int = 6) -> str:
    """Render recent conversation turns into a prompt section (oldest→newest)."""
    if not history:
        return ""
    recent = history[-(max_turns * 2):]  # last N turns (user+assistant pairs)
    lines = ["=== 对话历史 ==="]
    for m in recent:
        role = "用户" if m.get("role") == "user" else "秘书"
        lines.append(f"{role}: {m.get('content', '')[:500]}")
    return "\n".join(lines)


def _extract_content(result: dict[str, Any]) -> str:
    """Pull the most useful content from the agent run result dict.

    Delegates to ``campus.mobile.inbound._extract_content`` (single source of
    truth for result→text extraction). Falls back to a JSON dump if unavailable.
    """
    try:
        from campus.mobile.inbound import _extract_content as _ec
        text = _ec(result)
        if text:
            return text
    except Exception:
        pass
    # last resort: compact JSON of non-meta keys
    try:
        slim = {k: v for k, v in result.items()
                if k not in ("ok", "run_id", "intent", "domain",
                             "selected_workflow", "status", "artifacts",
                             "error", "multiagent", "real_llm", "mode")}
        if slim:
            return json.dumps(slim, ensure_ascii=False)[:1500]
    except Exception:
        pass
    return ""


def compose_reply(message: str, run_result: dict[str, Any],
                  persona_name: str = "default",
                  history: Optional[list[dict[str, Any]]] = None,
                  memory_snippet: str = "",
                  preferences_block: str = "") -> dict[str, Any]:
    """Compose a persona-styled natural-language reply from a run result.

    Returns ``{"reply", "persona", "source_mode", "needs_clarify",
    "clarify_options"}``.

    - If the run result itself signals ambiguity (``needs_clarify`` with
      ``clarify_options``), the reply asks the user to confirm — this powers the
      fuzzy-lecture-path and any other confirm-before-proceed flow.
    - Requires a real LLM. If LLM is unavailable, raises RuntimeError (caller
      returns an error to the user — no silent template fallback).
    - PREFERENCES are injected every turn via ``preferences_block`` (full-layer,
      not retrieved) — see ``campus.memory.preferences.load_preferences_block``.
    """
    from campus.runtime.llm_config import require_real_llm

    persona_name = (persona_name or "default").lower()
    needs_clarify = bool(run_result.get("needs_clarify"))
    clarify_options = run_result.get("clarify_options") or []

    # ---- LLM required (no offline fallback) ----
    real, status = require_real_llm("auto")
    if not real:
        raise RuntimeError(
            "LLM 未接入。请配置 GLM_API_KEY 到 ~/.hermes/.env 并确保 hermes_cli 可导入。"
            f" 当前状态: {status.get('readiness', 'unknown')}")

    # ---- LLM-composed reply ----
    content = _extract_content(run_result)
    status_val = run_result.get("status", "")
    domain = run_result.get("domain", "")
    intent = run_result.get("intent", "")
    error = run_result.get("error", "")

    from campus.personas.loader import select, apply_to_prompt
    persona = select(persona_name)

    base_parts = [
        "你是用户的专属校园秘书 Campus。请根据下面的任务执行结果，用自然语言向用户回复。",
        "要求：",
        "- 用亲切、简洁的中文口语回复（像微信/飞书聊天），不要用 markdown 表格或大段标题堆砌。",
        "- 先给出结论/成果，再附上关键细节；如果生成了产物（计划、知识图谱、检索结果等），简述内容并告诉用户可在侧边栏或产物区查看。",
        "- 如果有 URL 或检索证据，自然地融入回复（如『推荐 GitHub 项目 X，⭐1234，因为…：url』）。",
        "- 不要暴露内部字段名（如 domain/intent/run_id）给用户，除非用户问。",
    ]
    if needs_clarify:
        base_parts.append(
            "- 本次任务需要用户先确认。请明确地把待选项列出来，问用户选哪个，"
            "不要替用户做决定。"
        )
    base_parts.extend([
        "",
        f"=== 用户消息 ===\n{message}",
    ])
    hist = format_history(history or [])
    if hist:
        base_parts.append("")
        base_parts.append(hist)
    # Phase 9.1: PREFERENCES injected every turn (full-layer, not retrieved)
    if preferences_block:
        base_parts.append("")
        base_parts.append(preferences_block)
    # memory_snippet still carries recalled TASK_LOG/KNOWLEDGE (semantic retrieval)
    if memory_snippet:
        base_parts.append("")
        base_parts.append("=== 相关记忆（语义检索） ===")
        base_parts.append(memory_snippet[:1200])
    base_parts.append("")
    base_parts.append("=== 任务执行结果（结构化） ===")
    if content:
        base_parts.append(content[:3000])
    else:
        base_parts.append(f"（领域：{domain}，意图：{intent}，状态：{status_val}）")
    if needs_clarify:
        opts = "\n".join(f"  {i+1}. {o}" for i, o in enumerate(clarify_options))
        base_parts.append("")
        base_parts.append(f"=== 待用户确认的选项 ===\n{opts}")
    if error:
        base_parts.append("")
        base_parts.append(f"=== 执行中的错误 ===\n{error[:500]}")
    base_prompt = "\n".join(base_parts)

    full_prompt = apply_to_prompt(persona, base_prompt)

    try:
        from campus.runtime.llm_turn import ask_llm
        text, _rc = ask_llm(full_prompt, model="glm-4.6", provider="zai")
        reply = (text or "").strip()
        if not reply:
            reply = "（未能生成回复，请稍后再试。）"
        source_mode = "real_llm"
    except RuntimeError:
        raise  # LLM-not-available error propagates to caller
    except Exception as e:
        # LLM call failed (timeout, network, etc.) — surface the error, no silent fallback
        raise RuntimeError(f"LLM 调用失败: {e}") from e

    return {"reply": reply, "persona": persona_name,
            "source_mode": source_mode, "needs_clarify": needs_clarify,
            "clarify_options": clarify_options}
