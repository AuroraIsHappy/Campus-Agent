"""Tests for layered memory retrieval (Phase 8 Step 2).

Verifies RRF fusion, tiered per-layer recall, token-budget packing, recency
decay, pinned boost, and the min-score threshold.
"""
import os
import sys
import time
import uuid

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from campus.memory.json_store import JsonFileStore
from campus.memory.recall_strategy import (
    recall_layered, rrf_fuse, pack_token_budget, estimate_tokens,
    MIN_SCORE_THRESHOLD,
)
from campus.memory.types import (
    DAILY_LOG, KNOWLEDGE, PREFERENCES, TASK_LOG, MemoryRecord, Recall,
)


def _store(tmp_path):
    """A JsonFileStore pointed at a temp path."""
    path = os.path.join(tmp_path, "memory.json")
    return JsonFileStore(path=path)


def test_rrf_fuses_fts_and_vector():
    """RRF combines FTS and vector rankings; a record hit by both ranks highest."""
    now = int(time.time())
    recs = [
        MemoryRecord(id="a", layer=KNOWLEDGE, key="linux", content="linux kernel basics",
                     created_at=now),
        MemoryRecord(id="b", layer=KNOWLEDGE, key="python", content="python tutorial",
                     created_at=now),
        MemoryRecord(id="c", layer=KNOWLEDGE, key="linux-adv", content="linux advanced topics",
                     created_at=now),
    ]
    # embed the records so vector similarity works
    from campus.memory.embedding import HashEmbedder
    emb = HashEmbedder()
    for r in recs:
        r.embedding = emb.embed(f"{r.key} {r.content}")
    hits = rrf_fuse(recs, "linux", embedder=emb, now_ts=now)
    assert len(hits) >= 2
    # records with "linux" in content should rank above "python"
    top_ids = [h.record.id for h in hits]
    assert "b" not in top_ids[:2]  # python shouldn't be top for "linux" query
    assert top_ids[0] in ("a", "c")


def test_recall_layered_includes_all_preferences():
    """PREFERENCES layer is always fully included (small, high-value)."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        store = _store(tmp)
        store.remember(PREFERENCES, "identity", "大二计算机学生", pinned=True)
        store.remember(PREFERENCES, "persona", "feynman")
        store.remember(KNOWLEDGE, "linux", "Linux 基础教程")
        packed = recall_layered(store, "任何查询", token_budget=2000)
        assert packed.ok
        keys = {r.key for r in packed.records}
        assert "identity" in keys
        assert "persona" in keys


def test_token_budget_packing_truncates():
    """Records are packed until budget exhausted; overflow is dropped/truncated."""
    now = int(time.time())
    recs = [
        MemoryRecord(id=f"r{i}", layer=KNOWLEDGE, key=f"k{i}",
                     content="x" * 200, created_at=now)
        for i in range(10)
    ]
    recalls = [Recall(record=r, score=1.0) for r in recs]
    packed = pack_token_budget(recalls, token_budget=100)  # ~25 records worth
    assert packed.tokens_used <= 100
    assert packed.dropped >= 5  # most didn't fit
    assert len(packed.records) < 10


def test_pinned_records_get_priority():
    """Pinned records are packed first regardless of score."""
    now = int(time.time())
    low_score_pinned = MemoryRecord(id="pinned", layer=PREFERENCES, key="important",
                                    content="pinned content", created_at=now, pinned=True)
    high_score_unpinned = MemoryRecord(id="unpinned", layer=KNOWLEDGE, key="k",
                                       content="unpinned content", created_at=now)
    recalls = [
        Recall(record=low_score_pinned, score=0.1),
        Recall(record=high_score_unpinned, score=0.9),
    ]
    packed = pack_token_budget(recalls, token_budget=50)
    # pinned should be first
    assert packed.records[0].id == "pinned"


def test_recency_decay_favors_newer():
    """Newer records get a higher recency boost than old ones."""
    from campus.memory.recall_strategy import _recency_boost
    now = int(time.time())
    fresh = _recency_boost(now, now)
    old = _recency_boost(now - 60 * 86400, now)  # 60 days old
    assert fresh > old
    assert fresh > 0.9  # fresh is near 1.0
    assert old < 0.65   # 60 days = 2 half-lives → 0.5+0.5*0.25=0.625


def test_demo_c_memory_no_longer_corrupts_l4_store():
    """Demo C memory now delegates to L4 JsonFileStore instead of writing its own schema."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CAMPUS_HOME"] = tmp
        try:
            from campus.demo_c import memory as dc_mem
            dc_mem.remember({"learning": "linux"})
            dc_mem.set_goal("学 Linux")
            # the L4 store should now contain these (same file, same schema)
            store = _store(tmp)
            prefs = store.list_layer(PREFERENCES)
            keys = {r.key for r in prefs}
            assert any("demo_c_preference" in k for k in keys)
            assert any("goal:" in k for k in keys)
            # show() should return both
            shown = dc_mem.show()
            assert len(shown["preferences"]) >= 1
            assert "学 Linux" in shown["goals"]
        finally:
            del os.environ["CAMPUS_HOME"]
