"""Layered memory retrieval strategy (Phase 8 Step 2).

The existing ``recall()`` is a flat hybrid FTS+vector scan with raw-score sum,
no layer stratification, no reranking, no budget — and crucially it is never
called by the generation path. This module provides a *tiered* retrieval policy
that distinguishes short-term task context from long-term preferences and packs
results into a token budget.

Layer-specific rules:
  - PREFERENCES: always include ALL (small, high-value, session context).
  - DAILY_LOG: today + recent N by date key (not relevance).
  - TASK_LOG: scoped by task_id if given, then relevance-ranked.
  - KNOWLEDGE: relevance top-k.
  - TASK_BOARD: structured query by status (not FTS).

Score fusion uses Reciprocal Rank Fusion (RRF) instead of raw FTS+vector sum,
so the two channels are normalized and a high lexical overlap can't drown out
a semantic match. Recency decay + pinned boost are applied after fusion.

Token budget packing: records are added in priority order (pinned → preferences
→ task-scoped → knowledge → daily) until the budget is exhausted; the
lowest-priority hit is truncated to fit.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from campus.memory.embedding import cosine_sim, tokenize
from campus.memory.in_memory import fts_score
from campus.memory.types import (
    DAILY_LOG, KNOWLEDGE, PREFERENCES, TASK_BOARD, TASK_LOG,
    MemoryRecord, Recall,
)

__all__ = ["recall_layered", "rrf_fuse", "pack_token_budget",
           "estimate_tokens", "MIN_SCORE_THRESHOLD", "RECENCY_HALF_LIFE_S"]

# Drop hits below this fused score (noise filter).
MIN_SCORE_THRESHOLD = 0.01
# Recency decay: a record's score halves every ~30 days (seconds).
RECENCY_HALF_LIFE_S = 30 * 86400
# RRF constant (standard k=60 dampens rank differences).
_RRF_K = 60


def _recency_boost(created_at: int, now_ts: int) -> float:
    """Multiplicative boost in (0.5, 1.0]: newer records score higher."""
    if not created_at:
        return 0.7  # unknown age → mild penalty
    age = max(0, now_ts - created_at)
    # exponential decay: score * 0.5^(age / half_life)
    import math
    return 0.5 + 0.5 * (0.5 ** (age / RECENCY_HALF_LIFE_S))


def rrf_fuse(records: list[MemoryRecord], query: str, *,
             embedder=None, q_vec: Optional[list[float]] = None,
             now_ts: int = 0) -> list[Recall]:
    """Reciprocal Rank Fusion of FTS + vector channels.

    RRF(d) = 1/(k + rank_fts(d)) + 1/(k + rank_vec(d))
    A record hit by only one channel gets a single term; both channels get two.
    Then recency decay + pinned boost are applied. Returns ALL fused hits
    (caller slices/packs).
    """
    now_ts = now_ts or int(time.time())
    # rank by FTS
    fts_scored = [(r, fts_score(query, r)) for r in records]
    fts_scored = [(r, s) for r, s in fts_scored if s > 0]
    fts_scored.sort(key=lambda t: t[1], reverse=True)
    fts_ranks = {id(r): i + 1 for i, (r, _) in enumerate(fts_scored)}

    # rank by vector
    vec_ranks: dict[int, int] = {}
    if embedder is not None or q_vec is not None:
        if q_vec is None and embedder is not None:
            q_vec = embedder.embed(query)
        if q_vec is not None:
            vec_scored = []
            for r in records:
                if not r.embedding:
                    continue
                s = cosine_sim(q_vec, r.embedding)
                if s > 0:
                    vec_scored.append((r, s))
            vec_scored.sort(key=lambda t: t[1], reverse=True)
            vec_ranks = {id(r): i + 1 for i, (r, _) in enumerate(vec_scored)}

    all_ids = set(fts_ranks) | set(vec_ranks)
    out: list[Recall] = []
    for r in records:
        rid = id(r)
        if rid not in all_ids:
            continue
        score = 0.0
        if rid in fts_ranks:
            score += 1.0 / (_RRF_K + fts_ranks[rid])
        if rid in vec_ranks:
            score += 1.0 / (_RRF_K + vec_ranks[rid])
        # recency decay
        score *= _recency_boost(r.created_at, now_ts)
        # pinned boost (x1.5)
        if r.pinned:
            score *= 1.5
        if score >= MIN_SCORE_THRESHOLD:
            out.append(Recall(record=r, score=score))
    out.sort(key=lambda rc: rc.score, reverse=True)
    return out


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token, min 1."""
    return max(1, len(text or "") // 4)


@dataclass
class PackedMemory:
    """Result of token-budget packing: the records that fit + a formatted snippet."""
    records: list[MemoryRecord] = field(default_factory=list)
    snippet: str = ""
    tokens_used: int = 0
    tokens_budget: int = 0
    dropped: int = 0

    @property
    def ok(self) -> bool:
        return bool(self.records)


def pack_token_budget(recalls: list[Recall], token_budget: int = 1500) -> PackedMemory:
    """Pack recall hits into a token budget in priority order.

    Priority: pinned → score-ranked. Each record's content is added until the
    budget is exhausted; the last fitting record is truncated to fit. Records
    that don't fit are counted in ``dropped``.
    """
    # sort: pinned first, then by score
    ordered = sorted(recalls, key=lambda rc: (not rc.record.pinned, -rc.score))
    packed: list[MemoryRecord] = []
    used = 0
    dropped = 0
    for rc in ordered:
        rec = rc.record
        est = estimate_tokens(rec.content)
        if used + est <= token_budget:
            packed.append(rec)
            used += est
        elif used < token_budget:
            # truncate this record to fit
            remaining = token_budget - used
            if remaining > 5:  # only if meaningful space left
                rec = MemoryRecord(
                    id=rec.id, layer=rec.layer, key=rec.key,
                    content=rec.content[:remaining * 4] + "…",
                    metadata=rec.metadata, created_at=rec.created_at,
                    embedding=None, pinned=rec.pinned)
                packed.append(rec)
                used += remaining
            dropped += 1
        else:
            dropped += 1
    # build a formatted snippet for prompt injection
    lines = []
    for rec in packed:
        tag = f"[{rec.layer}]{' ★' if rec.pinned else ''}"
        lines.append(f"{tag} {rec.key}: {rec.content}")
    return PackedMemory(records=packed, snippet="\n".join(lines),
                        tokens_used=used, tokens_budget=token_budget,
                        dropped=dropped)


def recall_layered(store, query: str, *, task_id: str = "",
                   token_budget: int = 1500, k_per_layer: int = 5,
                   now_ts: int = 0) -> PackedMemory:
    """Tiered retrieval: per-layer rules → RRF fusion → token-budget packing.

    This is the function the generation path should call to get a memory snippet
    for prompt injection. It never raises (returns empty PackedMemory on failure).
    """
    now_ts = now_ts or int(time.time())
    try:
        embedder = getattr(store, "embedder", None) or getattr(
            getattr(store, "_store", None), "embedder", None)
    except Exception:
        embedder = None
    try:
        q_vec = embedder.embed(query) if embedder else None
    except Exception:
        q_vec = None

    recalls: list[Recall] = []

    # 1. PREFERENCES — always all (small, high-value)
    try:
        prefs = store.list_layer(PREFERENCES)
        for r in prefs:
            recalls.append(Recall(record=r, score=1.0 if r.pinned else 0.8))
    except Exception:
        pass

    # 2. TASK_LOG — scoped by task_id if given, then RRF
    try:
        task_recs = store.list_layer(TASK_LOG)
        if task_id:
            task_recs = [r for r in task_recs
                         if task_id in (r.key or "") or task_id in (r.content or "")
                         or task_id in str(r.metadata)]
        recalls.extend(rrf_fuse(task_recs, query, embedder=embedder,
                                q_vec=q_vec, now_ts=now_ts))
    except Exception:
        pass

    # 3. KNOWLEDGE — RRF top-k
    try:
        knowledge_recs = store.list_layer(KNOWLEDGE)
        k_hits = rrf_fuse(knowledge_recs, query, embedder=embedder,
                          q_vec=q_vec, now_ts=now_ts)[:k_per_layer]
        recalls.extend(k_hits)
    except Exception:
        pass

    # 4. DAILY_LOG — recent N by date (not relevance)
    try:
        daily = store.list_layer(DAILY_LOG)
        daily.sort(key=lambda r: r.created_at, reverse=True)
        for r in daily[:3]:
            recalls.append(Recall(record=r, score=0.5))
    except Exception:
        pass

    # 5. TASK_BOARD — by status (not FTS); skip for prompt injection (structured)
    # (task board items are shown in the UI, not injected into LLM prompts)

    return pack_token_budget(recalls, token_budget=token_budget)
