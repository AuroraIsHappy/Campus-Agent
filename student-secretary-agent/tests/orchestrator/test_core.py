"""P2-D1/D2: DAG topology validation + adversarial-pair verdict routing."""
import pytest

from campus.orchestrator.dag import (
    VERDICT_PASS, VERDICT_PENDING, VERDICT_REWORK,
    create_adversarial_pair, gate_verdict, topo_order, validate_dag, verdict_decision,
)
from campus.odyssey.orchestrator import Orchestrator
from campus.runtime.in_memory import InMemoryKanban
from campus.runtime.ports import (
    APPROVE, BLOCKED, CyclicDAGError, MissingParentError, REJECT,
)


# --- P2-D1: DAG topology ----------------------------------------------------
def test_topo_order_diamond():
    m = {"a": [], "b": ["a"], "c": ["a"], "d": ["b", "c"]}
    order = topo_order(m)
    assert order[0] == "a" and order[-1] == "d"
    assert order.index("a") < order.index("b") < order.index("d")
    assert order.index("a") < order.index("c") < order.index("d")


def test_dag_cycle_rejected():
    with pytest.raises(CyclicDAGError):
        validate_dag({"a": ["b"], "b": ["a"]})


def test_dag_self_loop_rejected():
    with pytest.raises(CyclicDAGError):
        validate_dag({"a": ["a"]})


def test_dag_missing_parent_rejected():
    with pytest.raises(MissingParentError):
        validate_dag({"a": ["ghost"]})


def test_dag_chain_validates():
    validate_dag({"a": [], "b": ["a"], "c": ["b"]})  # no raise


# --- P2-D2: adversarial-pair verdict routing --------------------------------
def test_adversarial_pair_structure():
    kb = InMemoryKanban("ap")
    orch = Orchestrator(kb)
    uid, gid = create_adversarial_pair(
        orch, upstream_role="writer", gate_role="reviewer",
        upstream_title="draft", gate_title="review", goal="g")
    assert kb.get_task(gid).parents == (uid,)
    assert kb.get_task(gid).status == BLOCKED   # gate waits on upstream


def _seed_pair_with_verdict(verdict):
    kb = InMemoryKanban("v")
    orch = Orchestrator(kb)
    uid, gid = create_adversarial_pair(
        orch, upstream_role="writer", gate_role="reviewer",
        upstream_title="draft", gate_title="review", goal="g")
    kb.complete_task(uid, summary="draft done")
    kb.complete_task(gid, summary="review", metadata={"verdict": verdict})
    return kb, gid


def test_verdict_decision_pass_on_approve():
    kb, gid = _seed_pair_with_verdict(APPROVE)
    assert gate_verdict(kb, gid) == APPROVE
    assert verdict_decision(kb, gid) == VERDICT_PASS


def test_verdict_decision_rework_on_reject():
    kb, gid = _seed_pair_with_verdict(REJECT)
    assert verdict_decision(kb, gid) == VERDICT_REWORK


def test_verdict_decision_pending_when_gate_not_done():
    kb = InMemoryKanban("vp")
    orch = Orchestrator(kb)
    uid, gid = create_adversarial_pair(
        orch, upstream_role="writer", gate_role="reviewer",
        upstream_title="draft", gate_title="review", goal="g")
    kb.complete_task(uid, summary="draft done")
    # gate not yet run
    assert verdict_decision(kb, gid) == VERDICT_PENDING
