"""Unit tests for campus.meta_agent.cost (S-COST): tiers, estimate, budget gate."""
import os
import sys

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from campus.meta_agent.cost import (
    CHEAP, MID, STRONG, DEFAULT_ROLE_TIER, TIER_MULT,
    tier_for, estimate_cost, route_table, BudgetGate,
)


def test_role_tier_mapping():
    assert tier_for("planner") == STRONG
    assert tier_for("writer") == STRONG
    assert tier_for("critic") == MID
    assert tier_for("reviewer") == MID
    assert tier_for("scheduler") == CHEAP
    assert tier_for("email") == CHEAP


def test_unknown_role_defaults_mid():
    assert tier_for("brand_new_role") == MID
    assert tier_for("") == MID


def test_estimate_cost_monotonic_in_tier():
    tokens = 4000
    c_cheap = estimate_cost("email", tokens)
    c_mid = estimate_cost("critic", tokens)
    c_strong = estimate_cost("planner", tokens)
    assert c_cheap < c_mid < c_strong          # cheap < mid < strong
    assert abs(c_strong - 4 * c_mid) < 1e-9     # strong = 4x mid


def test_estimate_cost_zero_tokens():
    assert estimate_cost("planner", 0) == 0.0


def test_route_table_default_and_merge():
    tbl = route_table()
    assert tbl["planner"]["tier"] == STRONG
    assert tbl["email"]["mult"] == TIER_MULT[CHEAP]
    cfg = {"roles": {"planner": {"tier": "cheap", "provider": "zai", "model": "glm-air"}}}
    tbl2 = route_table(cfg)
    assert tbl2["planner"]["tier"] == CHEAP
    assert tbl2["planner"]["provider"] == "zai"
    assert tbl2["planner"]["model"] == "glm-air"


def test_route_table_ignores_bad_tier():
    cfg = {"roles": {"planner": {"tier": "nonsense"}}}
    tbl = route_table(cfg)
    assert tbl["planner"]["tier"] == STRONG


def test_budget_gate_allows_until_exceeded():
    gate = BudgetGate(budget=10.0)
    cost1, ok1 = gate.charge("email", 1000)     # 0.25
    cost2, ok2 = gate.charge("planner", 1000)   # 4.0
    assert ok1 and ok2
    assert gate.spent == 4.25
    assert not gate.over_budget
    cost3, ok3 = gate.charge("planner", 10_000)  # 40.0 >> remaining
    assert not ok3
    assert gate.spent == 4.25
    assert len(gate.log()) == 2


def test_budget_gate_exact_boundary_allowed():
    gate = BudgetGate(budget=4.0)
    cost, ok = gate.charge("planner", 1000)     # exactly 4.0
    assert ok and abs(cost - 4.0) < 1e-9
    assert gate.remaining == 0.0
    _, ok2 = gate.charge("email", 1)
    assert not ok2
