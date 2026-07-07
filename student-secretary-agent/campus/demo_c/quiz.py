"""Daily quiz generator for Demo C (LLM-backed + pure parser)."""
from __future__ import annotations
import argparse, json
from typing import List
from .types import Quiz, QuizQuestion
from ._llm import ask_llm, extract_json

PROMPT_TMPL = (
    "You are a study-quiz author. For the topic below, write {n} concise practice "
    "questions for a beginner ~20-min self-study session. Return ONLY minified JSON, "
    "no prose, no code fence, exactly this shape: "
    "{{\"questions\":[{{\"q\":\"...\",\"answer\":\"...\",\"explanation\":\"...\"}}]}}\n"
    "Topic: {topic}\nContext resource: {resource}"
)


def parse_quiz(raw, topic="", day=1):
    """Parse LLM quiz output into a Quiz. Pure / unit-testable."""
    data = extract_json(raw) if raw else None
    qs: List[QuizQuestion] = []
    if isinstance(data, dict) and isinstance(data.get("questions"), list):
        for item in data["questions"]:
            if not isinstance(item, dict):
                continue
            q = str(item.get("q") or item.get("question") or "").strip()
            a = str(item.get("answer") or "").strip()
            if not q:
                continue
            opts = item.get("options") if isinstance(item.get("options"), list) else None
            qs.append(QuizQuestion(q=q, answer=a,
                                   explanation=str(item.get("explanation") or "").strip(),
                                   options=opts))
    return Quiz(day=day, topic=topic, questions=qs)


def generate_quiz(topic, resource="", n=3, model="glm-4.5-air", retries=1):
    quiz = parse_quiz("", topic=topic, day=1)
    for _attempt in range(retries + 1):
        prompt = PROMPT_TMPL.format(n=n, topic=topic, resource=resource or "(none)")
        text, rc = ask_llm(prompt, model=model)
        quiz = parse_quiz(text, topic=topic, day=1)
        if quiz.questions:
            return quiz
    return quiz


def _main():
    ap = argparse.ArgumentParser(description="Generate a daily quiz via GLM.")
    ap.add_argument("--topic", required=True)
    ap.add_argument("--resource", default="")
    ap.add_argument("-n", type=int, default=3)
    args = ap.parse_args()
    quiz = generate_quiz(args.topic, args.resource, args.n)
    out = {"day": quiz.day, "topic": quiz.topic,
           "questions": [{"q": q.q, "answer": q.answer,
                          "explanation": q.explanation} for q in quiz.questions]}
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()
