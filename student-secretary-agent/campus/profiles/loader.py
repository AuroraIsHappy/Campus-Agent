"""Role profile loader (architecture §4.2, P2-P1/P2-P2).

Loads the per-role YAMLs under ``campus/profiles/`` and resolves each role to a
``{provider, model}`` via ``~/.campus/routing.yaml`` (user-editable, vendor-neutral).
Resolution precedence: routing.roles[role] -> routing.default -> the profile's own
defaults. A missing routing file is fine (profile defaults win).
"""
from __future__ import annotations
import os
from typing import Any, Optional

import yaml

__all__ = ["ProfileLoader", "DEFAULT_ROUTING_PATH", "ROLES"]

DEFAULT_ROUTING_PATH = os.path.expanduser("~/.campus/routing.yaml")

# The 9 Phase-2 roles (architecture §4.2).
ROLES = (
    "planner", "critic", "researcher", "source_verifier", "source_ranker",
    "writer", "reviewer", "scheduler", "meta_agent",
)


class ProfileLoader:
    def __init__(self, profiles_dir: Optional[str] = None,
                 routing: Optional[dict[str, Any]] = None,
                 routing_path: Optional[str] = None) -> None:
        if profiles_dir is None:
            profiles_dir = os.path.dirname(os.path.abspath(__file__))
        self.profiles_dir = profiles_dir
        self.routing = routing if routing is not None else self._load_routing(routing_path)
        self._cache: Optional[dict[str, dict]] = None

    # --- routing ---------------------------------------------------------
    def _load_routing(self, routing_path: Optional[str]) -> dict[str, Any]:
        path = routing_path or DEFAULT_ROUTING_PATH
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data if isinstance(data, dict) else {}
        except FileNotFoundError:
            return {}
        except yaml.YAMLError:
            return {}

    def resolve(self, role: str) -> tuple[str, str]:
        """Return (provider, model) for ``role`` (routing wins over profile)."""
        roles = self.routing.get("roles", {}) or {}
        default = self.routing.get("default", {}) or {}
        prof = (self.load_all().get(role) or {})
        entry = roles.get(role) or default or {}
        provider = entry.get("provider") or prof.get("provider") or "zai"
        model = entry.get("model") or prof.get("model") or "glm-4.6"
        return provider, model

    # --- profiles --------------------------------------------------------
    def load_all(self) -> dict[str, dict[str, Any]]:
        if self._cache is not None:
            return self._cache
        out: dict[str, dict] = {}
        if not os.path.isdir(self.profiles_dir):
            self._cache = out
            return out
        for fn in sorted(os.listdir(self.profiles_dir)):
            if not fn.endswith((".yaml", ".yml")) or fn.startswith("_"):
                continue
            path = os.path.join(self.profiles_dir, fn)
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                continue
            name = data.get("name") or os.path.splitext(fn)[0]
            out[name] = data
        self._cache = out
        return out

    def get(self, role: str) -> dict[str, Any]:
        """Return the profile dict for ``role`` with resolved provider/model."""
        prof = dict(self.load_all().get(role) or {"name": role, "role": role})
        provider, model = self.resolve(role)
        prof["provider"] = provider
        prof["model"] = model
        return prof

    def validate(self) -> list[str]:
        """Return list of roles with invalid schema (empty == all valid).

        toolset may be an empty list (Critic/Reviewer/SourceRanker are reasoning-only).
        """
        problems = []
        for name, prof in self.load_all().items():
            if not str(prof.get("system_prompt", "")).strip():
                problems.append(f"{name}: missing system_prompt")
            if not isinstance(prof.get("toolset"), list):
                problems.append(f"{name}: missing/invalid toolset")
            if not prof.get("model"):
                problems.append(f"{name}: missing model")
        return problems
