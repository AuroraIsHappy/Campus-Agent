"""Onboarding wizard (architecture §4.4, S-ONBOARD).

Natural-language onboarding for non-CS users. Collects identity / major / persona /
provider keys via an **injected** ``ask`` function (a real chat channel plugs in here;
tests pass a canned dict). Produces a ``UserProfile`` with recommended skills. No LLM
required for the deterministic path — the wizard is a guided form, not a free chat.
"""
from __future__ import annotations
import re
from typing import Callable, Iterable, Optional

from campus.meta_agent.types import NON_ANTHROPIC_PROVIDERS, UserProfile

__all__ = ["OnboardingWizard", "recommend_skills", "PROVIDER_ALIASES", "PERSONA_ALIASES"]

AskFn = Callable[[str], str]

_PROVIDER_SPLIT = re.compile(r"[,，;\s]+")

# User-facing provider names -> canonical provider id (matches routing.yaml alias note:
# glm/zhipu/z-ai/z.ai -> zai). Lets non-CS users type friendly names at onboarding.
PROVIDER_ALIASES = {
    "glm": "zai", "zhipu": "zai", "z-ai": "zai", "z.ai": "zai", "智谱": "zai",
    "通义": "qwen", "tongyi": "qwen", "千问": "qwen",
    "kimi": "moonshot", "月之暗面": "moonshot",
    "deepseek": "deepseek", "ds": "deepseek",
    "ollama": "ollama", "local": "local", "本地": "local",
}

# Onboarding prompts persona choice with Chinese labels; map them to persona names.
PERSONA_ALIASES = {
    "默认": "default", "default": "default",
    "费曼": "feynman", "feynman": "feynman",
    "鲁迅": "lu_xun", "lu_xun": "lu_xun",
}


class OnboardingWizard:
    """5-minute onboarding. ``ask`` maps a question string to an answer string."""

    QUESTIONS: list[tuple[str, str]] = [
        ("identity", "你的身份是？（例如：大二学生）"),
        ("major", "你的专业是？"),
        ("year", "你的年级或入学年份？（可留空）"),
        ("persona", "想要哪种秘书风格？默认 / 费曼 / 鲁迅"),
        ("providers", "你有哪些模型 API key？逗号分隔：glm / deepseek / qwen / openai"),
    ]

    def __init__(self, ask: AskFn, personas: Optional[Iterable[str]] = None) -> None:
        self.ask = ask
        self.personas = tuple(personas) if personas else ("default", "feynman", "lu_xun")

    def run(self) -> UserProfile:
        answers: dict[str, str] = {}
        for key, question in self.QUESTIONS:
            answers[key] = (self.ask(question) or "").strip()

        provider_keys: dict[str, str] = {}
        for tok in _PROVIDER_SPLIT.split(answers.get("providers", "")):
            tok = tok.strip().lower()
            norm = PROVIDER_ALIASES.get(tok, tok)
            if norm in NON_ANTHROPIC_PROVIDERS:
                provider_keys[norm] = "set"

        raw_persona = answers.get("persona", "default").strip().lower()
        persona = PERSONA_ALIASES.get(raw_persona, raw_persona)
        if persona not in self.personas:
            persona = "default"

        profile = UserProfile(
            identity=answers.get("identity", ""),
            major=answers.get("major", ""),
            year=answers.get("year", ""),
            persona=persona,
            provider_keys=provider_keys,
        )
        profile.recommended_skills = recommend_skills(profile)
        return profile


def recommend_skills(profile: UserProfile) -> list[str]:
    """Light rule-based recommendation from major (extensible)."""
    major = (profile.major or "").lower()
    stem = any(k in major for k in ("计算机", "computer", "cs", "软件", "软工", "计科", "data", "ai"))
    out = ["memory_recall", "secretary_report"]
    if stem:
        out = ["research_web", "github_tool", "code_runner"] + out
    else:
        out = ["schedule_plan", "draft_email", "citation_gen"] + out
    return out
