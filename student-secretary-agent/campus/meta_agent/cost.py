"""Cost routing + budget gate (Phase 5 S-COST).

Maps each role to a cost tier (cheap / mid / strong, mirroring Haiku / Sonnet /
Opus-style split) and estimates per-role spend from token counts. ``BudgetGate``
accumulates spend for a long-running task and refuses to exceed the budget --
the cost-side counterpart to ``Supervisor``'s round/cost gates.

Vendor-neutral: tiers are abstract multipliers, not vendor names. A real
``routing.yaml`` (provider/model per role) is consumed by ``route_table`` but
not required -- the default tier table is enough to satisfy S-COST deterministically.
"""
from __future__ import annotations
from typing import Any, Optional

__all__ = [
    "CHEAP", "MID", "STRONG", "CostTier",
    "DEFAULT_ROLE_TIER", "TIER_MULT",
    "tier_for", "estimate_cost", "route_table", "BudgetGate",
]

CHEAP = "cheap"     # Haiku-style: fast/cheap roles (scheduler, email)
MID = "mid"         # Sonnet-style: gates (critic, reviewer, verifier)
STRONG = "strong"   # Opus-style: heavy reasoning (planner, writer, researcher)
CostTier = str

# role -> tier. Aligned with campus/profiles/*.yaml role set.
DEFAULT_ROLE_TIER: dict[str, CostTier] = {
    "planner": STRONG,
    "researcher": STRONG,
    "writer": STRONG,
    "source_verifier": MID,
    "source_ranker": MID,
    "critic": MID,
    "reviewer": MID,
    "meta_agent": STRONG,
    "scheduler": CHEAP,
    "email": CHEAP,
}

# relative price multiplier per tier (tokens priced in arbitrary units; the
# gate compares ratios, so the absolute scale does not matter for S-COST).
TIER_MULT: dict[CostTier, float] = {CHEAP: 0.25, MID: 1.0, STRONG: 4.0}


def tier_for(role: str) -> CostTier:
    """Tier for a role; unknown roles default to MID (safe middle)."""
    return DEFAULT_ROLE_TIER.get((role or "").strip(), MID)


def estimate_cost(role: str, tokens: int, *, price_per_1k: float = 1.0) -> float:
    """Estimated cost = (tokens/1000) * tier_multiplier * price_per_1k.

    Monotonic in tier: strong > mid > cheap for the same token count.
    """
    if tokens <= 0:
        return 0.0
    mult = TIER_MULT[tier_for(role)]
    return (tokens / 1000.0) * mult * max(0.0, price_per_1k)


def route_table(routing_config: Optional[dict[str, Any]] = None) -> dict[str, dict]:
    """Merge default tiers with an optional routing config (provider/model per role).

    Acceptance S-MODELCONFIG/S-COST: the table is vendor-neutral (tier) yet
    carries the user's provider/model when supplied. Output keyed by role.
    """
    table: dict[str, dict] = {}
    for role, tier in DEFAULT_ROLE_TIER.items():
        table[role] = {"tier": tier, "mult": TIER_MULT[tier]}
    if routing_config:
        roles = routing_config.get("roles") or {}
        for role, cfg in (roles or {}).items():
            tier = cfg.get("tier") if isinstance(cfg, dict) else None
            if tier in TIER_MULT:
                table[role] = {"tier": tier, "mult": TIER_MULT[tier],
                               "provider": cfg.get("provider"),
                               "model": cfg.get("model")}
    return table


class BudgetGate:
    """Accumulates task cost; ``charge`` refuses once the budget is exhausted.

    Mirrors the Supervisor cost gate: long-running tasks that overshoot their
    budget are stopped (returns allowed=False) instead of silently overspending.
    """

    def __init__(self, budget: float):
        self.budget = max(0.0, float(budget or 0))
        self._spent = 0.0
        self._log: list[tuple[str, int, float]] = []

    @property
    def spent(self) -> float:
        return self._spent

    @property
    def remaining(self) -> float:
        return max(0.0, self.budget - self._spent)

    @property
    def over_budget(self) -> bool:
        return self._spent > self.budget

    def charge(self, role: str, tokens: int, *, price_per_1k: float = 1.0) -> tuple[float, bool]:
        """Estimate cost for (role, tokens); allow only if it fits the budget.

        Returns (cost, allowed). A charge that would cross the budget is NOT
        applied (the caller must escalate / re-route to a cheaper tier).
        """
        cost = estimate_cost(role, tokens, price_per_1k=price_per_1k)
        if self._spent + cost > self.budget + 1e-9:
            return cost, False
        self._spent += cost
        self._log.append((role, tokens, cost))
        return cost, True

    def log(self) -> list[tuple[str, int, float]]:
        return list(self._log)
