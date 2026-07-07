"""L4 Memory end-to-end (P4-M3): cross-session recall via JsonFileStore.

Demonstrates S-MEMORY deterministically: one instance writes to a JSON file, a fresh
instance loading the same file remembers everything (FTS AND vector, since embeddings
are persisted). No Hermes / no network / no real model.
"""
from __future__ import annotations

from campus.memory import compress as compress_mod
from campus.memory.json_store import JsonFileStore
from campus.memory.types import PREFERENCES, TASK_LOG, KNOWLEDGE


def _path(tmp_path) -> str:
    return str(tmp_path / "memory.json")


def test_cross_session_fts_recall(tmp_path):
    # session 1: onboarded user — major + a course in the knowledge layer
    s1 = JsonFileStore(path=_path(tmp_path))
    s1.remember(PREFERENCES, "major", "计算机科学 专业")
    s1.remember(KNOWLEDGE, "course-linux", "正在学习 linux 操作系统 与 shell 脚本")

    # session 2: brand-new instance, same file -> remembers
    s2 = JsonFileStore(path=_path(tmp_path))
    hits = s2.recall("linux shell", mode="fts")
    assert hits and hits[0].record.key == "course-linux"
    pref = s2.get(PREFERENCES, "major")
    assert pref is not None and "计算机科学" in pref.content


def test_cross_session_vector_recall_uses_persisted_embeddings(tmp_path):
    s1 = JsonFileStore(path=_path(tmp_path))
    s1.remember(KNOWLEDGE, "git", "git 版本控制 分支 合并 工作流")

    s2 = JsonFileStore(path=_path(tmp_path))
    hits = s2.recall("git 分支", mode="vector")
    assert hits and hits[0].record.key == "git"


def test_cross_session_forget_persists(tmp_path):
    s1 = JsonFileStore(path=_path(tmp_path))
    rid = s1.remember(PREFERENCES, "tmp", "scratch")
    assert s1.forget(rid) is True

    s2 = JsonFileStore(path=_path(tmp_path))
    assert s2.get(PREFERENCES, "tmp") is None
    assert s2.all() == []


def test_full_lifecycle_compress_then_recall_in_new_session(tmp_path):
    """Session 1 accumulates prefs + old task logs; compress sediments the task logs into
    a long-term preference; session 2 recalls both the raw prefs and the sediment."""
    s1 = JsonFileStore(path=_path(tmp_path))
    s1.remember(PREFERENCES, "major", "计算机科学")
    s1.remember(PREFERENCES, "persona", "费曼")
    # old task-log entries (e.g. a finished long-horizon task)
    s1.remember(TASK_LOG, "run-1", "demo A 邮件外联",
                metadata={"summary": "完成 demo A 策划案与外联邮件草稿"}, created_at=1000)
    s1.remember(TASK_LOG, "run-2", "demo C linux",
                metadata={"summary": "为用户排了 30 天 linux 学习计划"}, created_at=2000)

    # compress the task log into a sedimented preference (Claude-dreams pattern)
    sediment = compress_mod.compress(s1.list_layer(TASK_LOG), created_at=5000)
    assert sediment is not None
    s1.remember(PREFERENCES, sediment.key, sediment.content, metadata=sediment.metadata,
                created_at=5000)

    # session 2: recall works on raw prefs AND the sedimented knowledge
    s2 = JsonFileStore(path=_path(tmp_path))
    prefs = s2.list_layer(PREFERENCES)
    pref_keys = {p.key for p in prefs}
    assert {"major", "persona", "sediment"} <= pref_keys
    # the sediment carries forward what the user actually did
    sediment_rec = s2.get(PREFERENCES, "sediment")
    assert "demo A" in sediment_rec.content or "linux" in sediment_rec.content
    # cross-session semantic recall on the sedimented content
    hits = s2.recall("策划案")
    assert hits, "new session must recall sedimented long-term memory"
