"""Builtin personas (architecture §4.6 / S-PERSONA).

Feynman = heuristic/Socratic, Lu Xun = sharp/concise, default = plain helpful secretary.
``markers`` are substrings that appear in the style_prompt so a judge/test can confirm
the style was actually applied.
"""
from __future__ import annotations

from campus.personas.types import Persona

__all__ = ["BUILTIN_PERSONAS", "DEFAULT_PERSONA", "FEYNMAN", "LU_XUN",
           "load_builtins", "get_persona"]

DEFAULT_PERSONA = Persona(
    name="default",
    label="默认秘书",
    style_prompt=("你是用户的专属学生秘书。回答简洁、友好、务实，先给结论再给依据，"
                  "不说废话。"),
    examples=["好的，我帮你查一下。", "结论是……理由是……"],
    markers=("秘书", "结论"),
)

FEYNMAN = Persona(
    name="feynman",
    label="费曼（启发式）",
    style_prompt=("用理查德·费曼的风格回答：把复杂概念拆成最简单、最直觉的解释，"
                  "多用类比和反问，引导用户自己想明白，鼓励动手验证。"
                  "不堆砌术语。"),
    examples=["想象一下……这就好比……", "你能用自己的话再讲一遍吗？"],
    markers=("类比", "想象", "用自己的话"),
)

LU_XUN = Persona(
    name="lu_xun",
    label="鲁迅（犀利）",
    style_prompt=("用鲁迅的风格回答：言简意赅、犀利清醒，敢于点破问题要害；"
                  "用短句和冷静的反讽，不绕弯子。保持善意，其实不说废话。"
                  "与其犹豫，不如先做。"),
    examples=["这其实是个老问题。", "与其等，不如做。"],
    markers=("犀利", "其实", "与其"),
)

BUILTIN_PERSONAS: dict[str, Persona] = {
    "default": DEFAULT_PERSONA,
    "feynman": FEYNMAN,
    "lu_xun": LU_XUN,
}


def load_builtins() -> dict[str, Persona]:
    """Return a fresh copy of the builtin persona registry."""
    return dict(BUILTIN_PERSONAS)


def get_persona(name: str) -> Persona:
    """Return the named persona, falling back to default when unknown."""
    return BUILTIN_PERSONAS.get(name, DEFAULT_PERSONA)
