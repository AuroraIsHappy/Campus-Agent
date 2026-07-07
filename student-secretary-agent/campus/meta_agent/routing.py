"""Vendor-neutral model routing (architecture §1/§7, S-MODELCONFIG).

Generate / write / validate ``~/.campus/routing.yaml`` (role -> {provider, model}).
Resolution at runtime already lives in ``campus.profiles.loader``; this module is the
**producer + validator**: it builds a routing config from onboarding (any non-Anthropic
provider the user has a key for), writes it as YAML the loader can read back, and checks
that at least one non-Anthropic provider is configured.
"""
from __future__ import annotations
import os
from typing import Any, Optional

import yaml

from campus.meta_agent.types import NON_ANTHROPIC_PROVIDERS, RoutingConfig

__all__ = [
    "generate_routing", "write_routing", "validate_routing",
    "DEFAULT_ROUTING_PATH", "HEAVY_ROLES", "ALL_ROLES",
    "PROVIDER_DEFAULT_MODEL",
]

DEFAULT_ROUTING_PATH = os.path.expanduser("~/.campus/routing.yaml")

HEAVY_ROLES = ("planner", "critic", "writer", "reviewer", "source_verifier", "meta_agent")
ALL_ROLES = ("planner", "critic", "researcher", "source_verifier", "source_ranker",
             "writer", "reviewer", "scheduler", "meta_agent", "email", "sub_agent")

PROVIDER_DEFAULT_MODEL = {
    "zai": "glm-4.6", "deepseek": "deepseek-chat", "qwen": "qwen-plus",
    "moonshot": "moonshot-v1-8k", "yi": "yi-large", "baichuan": "baichuan2-turbo",
    "openai": "gpt-4o-mini", "ollama": "llama3", "local": "local",
}
STRONG_FALLBACK = "glm-4.6"
CHEAP_FALLBACK = "glm-4.5-air"


def _model_for(role: str, role_model_map: Optional[dict]) -> str:
    if role_model_map and role_model_map.get(role):
        return role_model_map[role]
    return STRONG_FALLBACK if role in HEAVY_ROLES else CHEAP_FALLBACK


def generate_routing(profile=None, providers: Optional[list] = None,
                     role_model_map: Optional[dict] = None) -> RoutingConfig:
    """Build a RoutingConfig. Default provider = first non-Anthropic key the user has."""
    keys: dict[str, str] = {}
    if profile is not None:
        keys.update(getattr(profile, "provider_keys", {}) or {})
    if providers:
        for p in providers:
            keys.setdefault(str(p).lower(), "")

    default_provider = "zai"
    for p in keys:
        if p in NON_ANTHROPIC_PROVIDERS:
            default_provider = p
            break
    default_model = PROVIDER_DEFAULT_MODEL.get(default_provider, STRONG_FALLBACK)

    roles: dict[str, dict[str, str]] = {}
    for role in ALL_ROLES:
        roles[role] = {"provider": default_provider, "model": _model_for(role, role_model_map)}

    return RoutingConfig(schema=1,
                         default={"provider": default_provider, "model": default_model},
                         roles=roles)


def write_routing(config: RoutingConfig, path: Optional[str] = None) -> str:
    path = path or DEFAULT_ROUTING_PATH
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    data = config.to_dict() if hasattr(config, "to_dict") else dict(config)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    return path


def validate_routing(config) -> list[str]:
    """Return problems (empty list == valid). Enforces S-MODELCONFIG non-Anthropic rule."""
    data = config.to_dict() if hasattr(config, "to_dict") else dict(config)
    problems: list[str] = []
    if data.get("schema") != 1:
        problems.append("schema must be 1")
    default = data.get("default") or {}
    if not default.get("provider") or not default.get("model"):
        problems.append("default missing provider/model")
    roles = data.get("roles") or {}
    if not roles:
        problems.append("no role mappings")
    for role, entry in roles.items():
        entry = entry or {}
        if not entry.get("provider") or not entry.get("model"):
            problems.append(f"{role}: missing provider/model")
    providers = {default.get("provider")} | {(e or {}).get("provider") for e in roles.values()}
    providers.discard(None)
    if not any(p in NON_ANTHROPIC_PROVIDERS for p in providers):
        problems.append("no non-Anthropic provider configured (S-MODELCONFIG)")
    return problems
