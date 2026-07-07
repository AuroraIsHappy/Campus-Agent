"""Deterministic text embedding (architecture §4.3 / §7).

No external model: a stable hash-bag over tokens, L2-normalized, fixed dim.
Same text -> same vector (no Date / no Math.random). CJK tokens are first-class so
Chinese content embeds. This is NOT a real semantic model, but it makes
semantically-overlapping texts share buckets -> non-zero cosine, which is enough to
exercise the vector recall path deterministically. Real models plug in via
``EmbedderPort`` without touching callers or tests.
"""
from __future__ import annotations
import hashlib
import math
import re

__all__ = ["HashEmbedder", "cosine_sim", "rank_by_similarity", "tokenize", "DEFAULT_DIM"]

DEFAULT_DIM = 128
_TOKEN_RE = re.compile(r"[0-9a-z一-鿿]+", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    """Tokenize for recall & embedding: ascii/cjk runs PLUS each CJK char as a unigram.

    CJK has no word spaces, so a query like ``策划案`` would otherwise never match inside
    a longer run like ``策划案与外联邮件草稿``. Emitting unigrams gives Chinese substring
    recall (both FTS overlap and shared embedding buckets) while ascii keeps clean
    word-level behavior. Same function is used for embed + recall so cosine stays
    consistent between query and content.
    """
    if not text:
        return []
    lowered = text.lower()
    runs = _TOKEN_RE.findall(lowered)
    out = list(runs)
    for run in runs:
        for ch in run:
            if "一" <= ch <= "鿿":
                out.append(ch)
    return out


class HashEmbedder:
    """Deterministic bag-of-tokens embedder.

    Each token is hashed (blake2b, stable) to pick a bucket index and a sign bit;
    +1/-1 is accumulated, then the vector is L2-normalized. The zero vector stays
    zero (handled by callers via cosine_sim's 0.0 short-circuit).
    """

    def __init__(self, dim: int = DEFAULT_DIM) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in tokenize(text):
            digest = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if (digest[4] & 1) == 0 else -1.0
            vec[bucket] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


def cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity; 0.0 for empty / zero / mismatched-zero vectors."""
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(x * x for x in a[:n]))
    nb = math.sqrt(sum(x * x for x in b[:n]))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def rank_by_similarity(query_vec: list[float], records: list, k: int) -> list:
    """records: iterable of objects with ``.embedding``. Returns list[(record, score)] desc."""
    scored = []
    for r in records:
        emb = getattr(r, "embedding", None)
        if not emb:
            continue
        s = cosine_sim(query_vec, emb)
        if s > 0:
            scored.append((r, s))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:k]
