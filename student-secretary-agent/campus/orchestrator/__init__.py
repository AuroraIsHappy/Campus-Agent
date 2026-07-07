"""L3 orchestration: DAG topology + adversarial-pair helpers (architecture §4.2)."""
from campus.orchestrator.dag import (
    validate_dag, topo_order, create_adversarial_pair,
    gate_verdict, verdict_decision,
)
