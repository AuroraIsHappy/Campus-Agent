"""L6 Persona data model (architecture §4.6)."""
from __future__ import annotations
from dataclasses import dataclass, field

__all__ = ["Persona"]


@dataclass
class Persona:
    """A reply style overlay.

    ``style_prompt`` is appended to a base system prompt; ``markers`` are substrings a
    judge or test can look for to confirm the style was applied (S-PERSONA).
    """
    name: str
    label: str
    style_prompt: str
    examples: list[str] = field(default_factory=list)
    markers: tuple[str, ...] = ()
