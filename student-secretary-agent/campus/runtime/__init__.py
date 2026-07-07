"""Campus runtime ports + adapters (architecture §C4②). Thin seam over Hermes Kanban."""
from campus.runtime.ports import (
    KanbanPort, SpawnFn, Task, DispatchBuckets, Verdict,
    OdysseyError, CyclicDAGError, MissingParentError,
    ProtocolViolationError, CostLimitExceeded,
    READY, RUNNING, DONE, BLOCKED, AWAITING_HUMAN, FAILED,
    APPROVE, REJECT, PENDING, VERDICT_KEY, SUMMARY_KEY,
)
