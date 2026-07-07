"""L4 Memory unit tests (P4-M1/M2/M4/M5).

Pure stdlib — no Hermes, no network, no real model. HashEmbedder is deterministic.
"""
from __future__ import annotations
import pytest

from campus.memory.embedding import HashEmbedder, cosine_sim
from campus.memory.in_memory import InMemoryStore, fts_score
from campus.memory.types import (
    ALL_LAYERS, MemoryRecord, PREFERENCES, TASK_LOG, KNOWLEDGE, Recall,
)
from campus.memory import ebbinghaus
from campus.memory import compress as compress_mod


# --- P4-M1 multi-layer schema -------------------------------------------------

def test_all_five_layers_present():
    assert ALL_LAYERS == ("preferences", "task_log", "task_board", "knowledge", "daily_log")


def test_remember_returns_id_and_separates_layers():
    store = InMemoryStore()
    pid = store.remember(PREFERENCES, "major", "computer science")
    kid = store.remember(KNOWLEDGE, "course-linux", "learning linux shell")
    assert pid.startswith("preferences-")
    assert kid.startswith("knowledge-")
    assert {r.layer for r in store.all()} == {PREFERENCES, KNOWLEDGE}
    assert len(store.list_layer(PREFERENCES)) == 1
    assert len(store.list_layer(KNOWLEDGE)) == 1


def test_get_and_forget():
    store = InMemoryStore()
    rid = store.remember(PREFERENCES, "persona", "feynman")
    assert store.get(PREFERENCES, "persona").id == rid
    assert store.get(PREFERENCES, "missing") is None
    assert store.forget(rid) is True
    assert store.forget(rid) is False           # idempotent second time
    assert store.get(PREFERENCES, "persona") is None


def test_unknown_layer_rejected():
    store = InMemoryStore()
    with pytest.raises(ValueError):
        store.remember("bogus", "k", "v")


def test_record_roundtrip():
    r = MemoryRecord(id="x-1", layer=PREFERENCES, key="k", content="c",
                     metadata={"a": 1}, created_at=42, pinned=True)
    d = r.to_dict()
    r2 = MemoryRecord.from_dict(d)
    assert r2 == r
    # embedding survives roundtrip as None
    assert r2.embedding is None


# --- P4-M2 retrieval: FTS + vector + hybrid -----------------------------------

def _seed_corpus(store: InMemoryStore):
    store.remember(KNOWLEDGE, "linux", "学习 linux 操作系统 shell 脚本 教程")
    store.remember(KNOWLEDGE, "pasta", "意大利面 食谱 番茄 罗勒 大蒜")


def test_fts_recall_ranks_token_overlap():
    store = InMemoryStore(embedder=None)        # FTS-only path
    _seed_corpus(store)
    hits = store.recall("linux shell", mode="fts")
    assert hits and hits[0].record.key == "linux"
    keys = {h.record.key for h in hits}
    assert "pasta" not in keys                  # disjoint vocab -> no FTS hit


def test_vector_recall_deterministic_and_ranks_overlap():
    e = HashEmbedder()
    # determinism: same text -> same vector
    assert e.embed("linux shell") == e.embed("linux shell")
    store = InMemoryStore(embedder=e)
    _seed_corpus(store)
    hits = store.recall("linux shell", mode="vector", k=2)
    assert hits, "vector recall must surface overlapping record"
    assert hits[0].record.key == "linux"        # shares tokens -> top
    # self-similarity is maximal
    self_sim = cosine_sim(e.embed("linux shell"), e.embed("linux shell"))
    assert self_sim == pytest.approx(1.0, abs=1e-9)


def test_hybrid_recall_combines_channels():
    store = InMemoryStore()
    _seed_corpus(store)
    hits = store.recall("linux", mode="hybrid")
    assert hits and hits[0].record.key == "linux"


def test_recall_layer_filter_and_k_and_empty():
    store = InMemoryStore()
    _seed_corpus(store)
    store.remember(PREFERENCES, "note", "linux is my focus")
    # layer filter restricts to preferences
    pref = store.recall("linux", layers=(PREFERENCES,), k=5)
    assert all(h.record.layer == PREFERENCES for h in pref)
    assert pref and pref[0].record.key == "note"
    # k limit
    assert len(store.recall("linux", k=1)) <= 1
    # empty query -> no FTS hits (vector may still return overlaps, so check fts mode)
    assert store.recall("", mode="fts") == []


def test_unknown_recall_mode_rejected():
    store = InMemoryStore()
    with pytest.raises(ValueError):
        store.recall("x", mode="bogus")


def test_fts_score_helper_bounds():
    r = MemoryRecord(id="k-1", layer=KNOWLEDGE, key="linux", content="shell tutorial")
    assert fts_score("linux", r) == 1.0         # all query tokens present
    assert fts_score("linux python", r) == 0.5  # half present
    assert fts_score("", r) == 0.0
    assert fts_score("linux", MemoryRecord(id="k-2", layer=KNOWLEDGE, key="", content="")) == 0.0


# --- P4-M4 Ebbinghaus ---------------------------------------------------------

def test_interval_sequence():
    assert ebbinghaus.interval_days(0) == 1
    assert ebbinghaus.interval_days(1) == 3
    assert ebbinghaus.interval_days(2) == 7
    assert ebbinghaus.interval_days(3) == 16
    assert ebbinghaus.interval_days(4) == 35
    # beyond table grows ~1.8x
    assert ebbinghaus.interval_days(5) == int(35 * 1.8)
    assert ebbinghaus.interval_days(6) == int(35 * 1.8 ** 2)


def test_next_review_adds_interval():
    t0 = 1_000_000
    assert ebbinghaus.next_review(0, t0) == t0 + 1 * 86_400
    assert ebbinghaus.next_review(2, t0) == t0 + 7 * 86_400


def test_advance_correct_increments_wrong_resets():
    assert ebbinghaus.advance(2, True) == 3
    assert ebbinghaus.advance(0, True) == 1
    assert ebbinghaus.advance(5, False) == 0    # wrong answer resets streak


def test_due_items_and_schedule():
    day = 86_400
    items = [
        {"key": "fresh", "last_ts": 0, "reps_correct": 0},   # due at 1d
        {"key": " mature", "last_ts": 0, "reps_correct": 2},  # due at 7d
    ]
    # at day 1: only the fresh item is due
    due = ebbinghaus.due_items(items, day)
    assert [d["key"].strip() for d in due] == ["fresh"]
    # at day 7: both due
    due7 = ebbinghaus.due_items(items, 7 * day)
    assert len(due7) == 2
    # schedule returns sorted (soonest first)
    sched = ebbinghaus.schedule(items)
    assert sched[0][0]["key"].strip() == "fresh"
    assert sched[1][1] > sched[0][1]


# --- P4-M5 compress / forget --------------------------------------------------

def test_default_summarizer_prefers_metadata_summary():
    recs = [
        MemoryRecord(id="t-1", layer=TASK_LOG, key="a", content="did X",
                     metadata={"summary": "shipped demo a"}),
        MemoryRecord(id="t-2", layer=TASK_LOG, key="b", content="wrote tests\nmore"),
    ]
    out = compress_mod.default_summarizer(recs)
    assert "- shipped demo a" in out
    assert "- wrote tests" in out          # falls back to first content line


def test_compress_sediments_non_pinned_records():
    recs = [
        MemoryRecord(id="t-1", layer=TASK_LOG, key="a", content="alpha",
                     metadata={"summary": "did alpha"}),
        MemoryRecord(id="t-2", layer=TASK_LOG, key="b", content="beta",
                     metadata={"summary": "did beta"}),
        MemoryRecord(id="t-3", layer=TASK_LOG, key="pin", content="keep me",
                     metadata={"summary": "pinned fact"}, pinned=True),
    ]
    sed = compress_mod.compress(recs, created_at=99)
    assert sed is not None
    assert sed.layer == PREFERENCES
    assert sed.key == "sediment"
    assert "did alpha" in sed.content and "did beta" in sed.content
    assert "pinned fact" not in sed.content   # pinned excluded
    assert sed.metadata["sedimented_from"] == 2


def test_compress_none_on_empty_or_blank():
    assert compress_mod.compress([]) is None
    only_pinned = [MemoryRecord(id="t-1", layer=TASK_LOG, key="p", content="",
                                pinned=True)]
    assert compress_mod.compress(only_pinned) is None
    blank = [MemoryRecord(id="t-2", layer=TASK_LOG, key="b", content="   ")]
    assert compress_mod.compress(blank) is None


def test_compress_uses_injected_summarizer():
    recs = [MemoryRecord(id="t-1", layer=TASK_LOG, key="a", content="whatever")]
    sed = compress_mod.compress(recs, summarizer=lambda rs: "CUSTOM")
    assert sed.content == "CUSTOM"


def test_prune_by_window_keeps_recent_and_pinned():
    now = 10_000
    recs = [
        MemoryRecord(id="t-1", layer=TASK_LOG, key="old", content="x", created_at=0),
        MemoryRecord(id="t-2", layer=TASK_LOG, key="new", content="x", created_at=now),
        MemoryRecord(id="t-3", layer=TASK_LOG, key="pin", content="x",
                     created_at=0, pinned=True),
    ]
    kept = compress_mod.prune_by_window(recs, now_ts=now, retention_seconds=5_000)
    keys = {r.key for r in kept}
    assert keys == {"new", "pin"}             # old non-pinned pruned


def test_recall_is_recall_objects():
    store = InMemoryStore()
    store.remember(KNOWLEDGE, "linux", "linux shell")
    hits = store.recall("linux")
    assert all(isinstance(h, Recall) for h in hits)


def test_cosine_sim_zero_and_empty_vectors():
    assert cosine_sim([], [1.0, 2.0]) == 0.0
    assert cosine_sim([0.0, 0.0], [1.0, 1.0]) == 0.0      # zero vector -> 0.0


def test_rank_by_similarity_orders_records():
    from campus.memory.embedding import rank_by_similarity
    e = HashEmbedder()
    records = [
        MemoryRecord(id="k-1", layer=KNOWLEDGE, key="linux", content="linux shell",
                     embedding=e.embed("linux shell")),
        MemoryRecord(id="k-2", layer=KNOWLEDGE, key="pasta", content="cooking pasta",
                     embedding=e.embed("cooking pasta")),
        MemoryRecord(id="k-3", layer=KNOWLEDGE, key="none", content="no embedding"),
    ]
    ranked = rank_by_similarity(e.embed("linux"), records, k=2)
    assert ranked and ranked[0][0].key == "linux"
    assert all(r.key != "none" for r, _ in ranked)        # missing embedding skipped
