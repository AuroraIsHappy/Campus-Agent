"""L5 Meta-Agent data models (architecture §4.4). Pure stdlib."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "UserProfile", "SkillEntry", "RoutingConfig", "ClassifyDecision",
    "NON_ANTHROPIC_PROVIDERS", "SKILL_SOURCES",
]

# providers that satisfy S-MODELCONFIG ("at least one non-Anthropic").
NON_ANTHROPIC_PROVIDERS = ("zai", "deepseek", "qwen", "openai", "ollama", "local", "moonshot", "baichuan", "yi")
SKILL_SOURCES = ("hermes", "cli_anything", "campus")


@dataclass
class UserProfile:
    """Result of onboarding. ``provider_keys`` maps provider -> key (redacted on dump)."""
    identity: str = ""
    major: str = ""
    year: str = ""
    persona: str = "default"
    provider_keys: dict[str, str] = field(default_factory=dict)
    recommended_skills: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity, "major": self.major, "year": self.year,
            "persona": self.persona,
            "provider_keys": {k: ("***set" if v else "") for k, v in self.provider_keys.items()},
            "recommended_skills": list(self.recommended_skills),
            "constraints": dict(self.constraints),
        }

    @property
    def has_non_anthropic_provider(self) -> bool:
        return any(p in NON_ANTHROPIC_PROVIDERS for p in self.provider_keys)


@dataclass
class SkillEntry:
    """One entry in the zero-config skill catalog."""
    name: str
    source: str               # one of SKILL_SOURCES
    category: str = ""
    installed: bool = False
    maintained: bool = True
    description: str = ""

    def reliability(self) -> float:
        """0..1: installed (+0.5), maintained (+0.3), known source (+0.2). Capped at 1.0."""
        score = 0.0
        if self.installed:
            score += 0.5
        if self.maintained:
            score += 0.3
        if self.source in SKILL_SOURCES:
            score += 0.2
        return min(score, 1.0)


@dataclass
class RoutingConfig:
    """Vendor-neutral role -> {provider, model} routing (S-MODELCONFIG)."""
    schema: int = 1
    default: dict[str, str] = field(default_factory=lambda: {"provider": "zai", "model": "glm-4.6"})
    roles: dict[str, dict[str, str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "default": dict(self.default),
            "roles": {k: dict(v) for k, v in self.roles.items()},
        }

    @property
    def providers(self) -> set[str]:
        out = {self.default.get("provider")}
        for entry in self.roles.values():
            if entry.get("provider"):
                out.add(entry["provider"])
        out.discard(None)
        return out

    @property
    def has_non_anthropic_provider(self) -> bool:
        return any(p in NON_ANTHROPIC_PROVIDERS for p in self.providers)


@dataclass
class ClassifyDecision:
    """Meta-Agent task classification."""
    kind: str                 # "short" | "long"
    reason: str = ""
    skills: list[str] = field(default_factory=list)
