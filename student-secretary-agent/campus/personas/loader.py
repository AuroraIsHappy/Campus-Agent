"""Persona loader + style application (architecture §4.6 / S-PERSONA).

``apply_to_prompt`` overlays a persona's style on a base system prompt. ``select`` looks
up by name across builtins (and an optional caller-supplied registry for custom personas).
"""
from __future__ import annotations
from typing import Iterable, Optional

from campus.personas.builtins import BUILTIN_PERSONAS, DEFAULT_PERSONA
from campus.personas.types import Persona

__all__ = ["select", "apply_to_prompt", "available_names"]

_STYLE_HEADER = "【人格风格】"


def select(name: str, personas: Optional[dict] = None) -> Persona:
    """Look up a persona by name. Falls back to default when unknown.

    ``personas`` may extend/override builtins (custom personas). name is case-insensitive.
    """
    registry = dict(BUILTIN_PERSONAS)
    if personas:
        registry.update(personas)
    return registry.get((name or "").strip().lower(), DEFAULT_PERSONA)


def apply_to_prompt(persona: Persona, base_prompt: str) -> str:
    """Overlay ``persona``'s style on ``base_prompt``.

    The result carries a ``[persona: <name>]`` tag and the style block so a downstream
    judge or test can confirm which style is active. Examples are included when present.
    """
    base = (base_prompt or "").rstrip()
    parts = [base, "", f"[persona: {persona.name}]", _STYLE_HEADER, persona.style_prompt]
    if persona.examples:
        parts.append("示例语气：")
        parts.extend(f"  - {ex}" for ex in persona.examples)
    return "\n".join(parts).strip()


def available_names(personas: Optional[dict] = None) -> list[str]:
    """Sorted persona names available to select() (builtins + any caller extras)."""
    registry = dict(BUILTIN_PERSONAS)
    if personas:
        registry.update(personas)
    return sorted(registry)
