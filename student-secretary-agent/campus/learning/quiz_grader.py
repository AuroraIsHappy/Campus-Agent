"""LLM-powered quiz grading (Phase 9 — replaces length-heuristic grading).

The existing ``phase7.quiz_grade`` scores answers by ``40 + len(text)*3`` — a
placeholder. This module grades semantically: compares the user's answer to the
reference answer via an LLM, producing a real score + feedback. Falls back to
the length heuristic when no LLM is available.
"""
from __future__ import annotations

from typing import Any

__all__ = ["llm_grade", "grade_quiz_answers"]


def llm_grade(question: str, reference: str, answer: str) -> dict[str, Any]:
    """Grade one answer against the reference using the LLM.

    Returns ``{"score": 0-100, "feedback": str, "correct": bool}``.
    Falls back to a length heuristic if no LLM is available.
    """
    from campus.runtime.llm_config import require_real_llm
    real, _status = require_real_llm("auto")

    if not real or not answer.strip():
        return _heuristic_grade(question, reference, answer)

    try:
        from campus.runtime.llm_turn import ask_llm, extract_json
        prompt = (
            "你是阅卷老师。请给学生的回答打分。\n\n"
            f"题目：{question}\n"
            f"参考答案：{reference}\n"
            f"学生回答：{answer}\n\n"
            "评分标准：0-100 分。关键点覆盖度 60%，表述准确性 30%，简洁度 10%。\n"
            "只返回 JSON：{\"score\": <0-100>, \"feedback\": \"<一句话评语>\"}。"
        )
        text, _rc = ask_llm(prompt, model="glm-4.6", provider="zai")
        data = extract_json(text)
        if isinstance(data, dict) and "score" in data:
            score = max(0, min(100, int(data["score"])))
            return {"score": score,
                    "feedback": str(data.get("feedback", ""))[:300],
                    "correct": score >= 70}
    except Exception:
        pass
    return _heuristic_grade(question, reference, answer)


def _heuristic_grade(question: str, reference: str, answer: str) -> dict[str, Any]:
    """Length-based fallback (mirrors the old phase7.quiz_grade logic)."""
    score = min(100, 40 + len(answer.strip()) * 3)
    correct = score >= 70
    feedback = "回答较简略，建议展开。" if not correct else "回答完整，继续加油。"
    return {"score": score, "feedback": feedback, "correct": correct}


def grade_quiz_answers(questions: list[dict[str, Any]],
                       answers: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Grade a batch of answers against their questions.

    ``questions``: [{id, question, answer, review_node_id}]
    ``answers``: [{question_id, answer, review_node_id}]
    Returns graded: [{question_id, score, feedback, correct, review_node_id}].
    """
    qmap = {q.get("id", ""): q for q in questions}
    graded = []
    for a in answers:
        qid = a.get("question_id") or a.get("id", "")
        q = qmap.get(qid, {})
        result = llm_grade(q.get("question", ""), q.get("answer", ""),
                           a.get("answer", ""))
        graded.append({
            "question_id": qid,
            "score": result["score"],
            "feedback": result["feedback"],
            "correct": result["correct"],
            "review_node_id": a.get("review_node_id") or q.get("review_node_id", ""),
        })
    return graded
