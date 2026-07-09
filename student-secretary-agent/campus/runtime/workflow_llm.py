"""Real-LLM workflow prompts for the five Phase 7 domains (Phase 8 Step 3).

Each domain workflow (learning/research/life/club/career) has a prompt template
that, when ``mode=real|auto`` and an LLM is available, produces real LLM-driven
content. When the LLM is unavailable or parsing fails, the caller falls back to
the deterministic ``phase7`` template (backward-compatible, hermetic tests).

The prompts ask for structured JSON output (parsed via ``extract_json``) so the
result shapes stay compatible with the existing API contracts.

This module is deliberately *prompt-only* — it does not contain business logic.
The actual workflow functions in ``phase7.py`` call ``llm_generate`` here with a
``domain`` + ``params``, and either get back real LLM content or None (→ fallback).
"""
from __future__ import annotations

from typing import Any, Optional


def llm_generate(domain: str, task: str, params: dict[str, Any],
                 *, memory_snippet: str = "") -> Optional[dict[str, Any]]:
    """Generate a domain workflow result via the real LLM.

    Returns a parsed dict on success, or None on any failure (caller falls back
    to the deterministic template). Never raises.
    """
    try:
        from campus.runtime.llm_turn import ask_llm, extract_json
        from campus.runtime.llm_config import require_real_llm

        real, status = require_real_llm("real")
        if not real:
            return None

        prompt = _build_prompt(domain, task, params, memory_snippet)
        raw, _rc = ask_llm(prompt, model="glm-4.6", provider="zai")
        if not raw or _rc != 0:
            return None
        parsed = extract_json(raw)
        if parsed and isinstance(parsed, dict):
            parsed.setdefault("source_mode", "real_llm")
            return parsed
        # LLM returned text, not JSON — wrap it as a summary
        return {"source_mode": "real_llm", "summary": raw[:2000], "raw_text": True}
    except Exception:
        return None


def _build_prompt(domain: str, task: str, params: dict[str, Any],
                  memory_snippet: str) -> str:
    """Build a domain-specific LLM prompt requesting structured JSON output."""
    ctx = ""
    if memory_snippet:
        ctx = f"\n=== 用户记忆 ===\n{memory_snippet}\n"

    if domain == "learning":
        return _learning_prompt(task, params, ctx)
    if domain == "research":
        return _research_prompt(task, params, ctx)
    if domain == "life":
        return _life_prompt(task, params, ctx)
    if domain == "club":
        return _club_prompt(task, params, ctx)
    if domain == "career":
        return _career_prompt(task, params, ctx)
    return f"你是校园秘书。请完成以下任务并返回 JSON：\n{task}\n{ctx}"


def _learning_prompt(task: str, params: dict, ctx: str) -> str:
    topic = params.get("topic", task)
    count = params.get("count", 5)
    if task == "flashcards":
        return (
            f"你是学习助手。为「{topic}」生成 {count} 张 flashcard。{ctx}\n"
            f"返回 JSON：{{\"flashcards\": [{{\"front\": \"问题\", \"back\": \"答案\", \"tags\": [\"{topic}\"]}}]}}"
        )
    if task == "quiz":
        return (
            f"你是学习助手。为「{topic}」生成 {count} 道复习 quiz 题。{ctx}\n"
            f"返回 JSON：{{\"questions\": [{{\"question\": \"题目\", \"answer\": \"参考答案\", \"rubric\": [\"评分标准\"]}}]}}"
        )
    return f"你是学习助手。完成学习任务：{task}（主题：{topic}）。{ctx}\n返回 JSON 结果。"


def _research_prompt(task: str, params: dict, ctx: str) -> str:
    if task == "github_trending":
        topic = params.get("topic", "AI")
        return (
            f"你是科研助手。推荐与「{topic}」相关的 3 个 GitHub 热门项目。{ctx}\n"
            f"返回 JSON：{{\"items\": [{{\"name\": \"repo\", \"url\": \"https://github.com/...\", "
            f"\"language\": \"Python\", \"stars\": 1000, \"reason\": \"推荐理由\"}}]}}"
        )
    if task == "format_check":
        title = params.get("title", "")
        return (
            f"你是科研助手。检查以下论文/稿件是否符合会议/期刊格式要求。标题：{title}。{ctx}\n"
            f"返回 JSON：{{\"items\": [{{\"name\": \"检查项\", \"passed\": true, \"detail\": \"说明\"}}]}}"
        )
    return f"你是科研助手。完成科研任务：{task}。{ctx}\n返回 JSON 结果。"


def _life_prompt(task: str, params: dict, ctx: str) -> str:
    if task == "travel_plan":
        dest = params.get("destination", "")
        days = params.get("days", 2)
        return (
            f"你是生活秘书。为「{dest}」制定 {days} 天旅行计划。{ctx}\n"
            f"返回 JSON：{{\"itinerary\": [{{\"day\": 1, \"morning\": \"\", \"afternoon\": \"\", \"evening\": \"\", \"budget\": 200}}]}}"
        )
    if task == "campus_guide":
        return (
            f"你是校园生活秘书。给出校园办事流程指南。{ctx}\n"
            f"返回 JSON：{{\"guides\": [{{\"title\": \"事项\", \"steps\": [\"步骤1\", \"步骤2\"]}}]}}"
        )
    return f"你是生活秘书。完成生活任务：{task}。{ctx}\n返回 JSON 结果。"


def _club_prompt(task: str, params: dict, ctx: str) -> str:
    if task == "meeting_minutes":
        topic = params.get("topic", "")
        notes = params.get("notes", "")
        return (
            f"你是社团秘书。根据以下会议笔记整理「{topic}」的会议纪要。笔记：{notes}。{ctx}\n"
            f"返回 JSON：{{\"minutes\": {{\"decisions\": [\"决议1\"], \"todo\": [\"待办1\"], \"next_meeting\": \"下次会议\"}}}}"
        )
    if task == "recruiting_copy":
        org = params.get("org", "")
        return (
            f"你是社团秘书。为「{org}」写招新文案。{ctx}\n"
            f"返回 JSON：{{\"copy\": {{\"headline\": \"\", \"body\": \"\", \"poster_points\": [\"亮点1\"]}}}}"
        )
    if task == "email_draft":
        purpose = params.get("purpose", "")
        return (
            f"你是社团秘书。写一封关于「{purpose}」的邮件草稿（不发送）。{ctx}\n"
            f"返回 JSON：{{\"email\": \"邮件正文\"}}"
        )
    return f"你是社团秘书。完成任务：{task}。{ctx}\n返回 JSON 结果。"


def _career_prompt(task: str, params: dict, ctx: str) -> str:
    if task == "interview_plan":
        role = params.get("role", "")
        return (
            f"你是职业顾问。为「{role}」制定面试准备计划。{ctx}\n"
            f"返回 JSON：{{\"plan\": [{{\"day\": 1, \"focus\": \"\", \"task\": \"\", \"minutes\": 45}}], "
            f"\"questions\": [\"面试题1\"]}}"
        )
    if task == "interview_practice":
        role = params.get("role", "")
        question = params.get("question", "")
        answer = params.get("answer", "")
        return (
            f"你是职业顾问。评估以下面试练习回答并给出改进建议。岗位：{role}。问题：{question}。回答：{answer}。{ctx}\n"
            f"返回 JSON：{{\"score\": 80, \"rubric\": [\"标准1\"], \"improvement_cues\": [\"建议1\"], "
            f"\"model_answer_outline\": [\"要点1\"], \"follow_ups\": [\"追问1\"]}}"
        )
    if task == "job_search":
        query = params.get("query", "")
        city = params.get("city", "")
        return (
            f"你是职业顾问。为「{query}」推荐 3 个适合大学生的实习岗位{'（城市：'+city+'）' if city else ''}。{ctx}\n"
            f"返回 JSON：{{\"jobs\": [{{\"id\": \"job_1\", \"title\": \"岗位名\", \"company\": \"公司\", "
            f"\"city\": \"城市\", \"url\": \"\", \"fit\": 90, \"reason\": \"推荐理由\"}}]}}"
        )
    return f"你是职业顾问。完成任务：{task}。{ctx}\n返回 JSON 结果。"
