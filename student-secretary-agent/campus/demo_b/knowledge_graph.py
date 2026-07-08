"""Knowledge-graph builder (Demo B B-F2).

``build_kg`` turns extracted lecture texts into a structured ``KnowledgeGraph``
(chapters / concepts / formulas / question types / key points). The actual node
extraction is an injectable ``extract_fn``: the default is a deterministic
heuristic (heading/bullet patterns) good enough for tests; a real LLM extractor
plugs in without changing the caller. No hallucination: nodes always cite their
``source_doc`` and only validated edges survive (``checkers.check_kg``).
"""
from __future__ import annotations
import hashlib
import re
from typing import Callable, Optional

from campus.demo_b.types import (
    ExtractedText, KGNode, KGEdge, KnowledgeGraph, KG_KINDS,
)

__all__ = ["ExtractFn", "default_extract_fn", "build_kg", "validate_kg"]

# extract_fn(text, source_doc) -> list[KGNode] (edges derived separately)
ExtractFn = Callable[[str, str], list[KGNode]]

_HEADING = re.compile(r"^\s{0,3}(#{1,6}\s+.+|第[一二三四五六七八九十百零\d]+[章节课].*|chapter\s+\d+.*)", re.I)
_BULLET = re.compile(r"^\s{0,3}([-*•]|\d+[.)])\s+(.+)")


def _nid(source_doc: str, kind: str, title: str) -> str:
    h = hashlib.md5(f"{source_doc}|{kind}|{title}".encode("utf-8")).hexdigest()[:10]
    return f"{kind}-{h}"


def default_extract_fn(text: str, source_doc: str) -> list[KGNode]:
    """Deterministic heuristic extractor: headings -> chapters, bullets -> concepts.

    Good enough to produce a non-empty, well-formed graph for tests; production
    swaps in an LLM-backed extractor via ``build_kg(extract_fn=...)``.
    """
    nodes: list[KGNode] = []
    if not text:
        return nodes
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        title = s.lstrip("#").lstrip("*-• ").strip()
        if not title:
            continue
        if _HEADING.match(s):
            nodes.append(KGNode(id=_nid(source_doc, "chapter", title),
                                kind="chapter", title=title, source_doc=source_doc))
        else:
            m = _BULLET.match(s)
            concept = m.group(2).strip() if m else title
            nodes.append(KGNode(id=_nid(source_doc, "concept", concept),
                                kind="concept", title=concept, source_doc=source_doc))
    return nodes


def build_kg(extracted: list[ExtractedText],
             extract_fn: Optional[ExtractFn] = None) -> KnowledgeGraph:
    """Build a KnowledgeGraph over the extracted corpus (B-F2).

    Dedupes nodes by (kind, title); links each chapter to the concepts that
    followed it within the same source doc. Empty/failed extractions contribute
    nothing but do not fail the build.
    """
    fn = extract_fn or default_extract_fn
    kg = KnowledgeGraph()
    seen: set[tuple[str, str]] = set()

    for et in extracted:
        if not (et.ok and et.chars > 0):
            continue
        src = et.doc.path
        if src not in kg.source_docs:
            kg.source_docs.append(src)
        nodes = fn(et.text or "", src) or []
        current_chapter: Optional[KGNode] = None
        for n in nodes:
            key = (n.kind, n.title)
            if key in seen:
                node = next(x for x in kg.nodes if x.kind == n.kind and x.title == n.title)
            else:
                seen.add(key)
                node = KGNode(id=n.id, kind=n.kind, title=n.title,
                              summary=n.summary, source_doc=src, refs=list(n.refs))
                kg.nodes.append(node)
            if n.kind == "chapter":
                current_chapter = node
            elif current_chapter is not None:
                kg.edges.append(KGEdge(src=current_chapter.id, dst=node.id, rel="contains"))
    return kg


def validate_kg(kg: KnowledgeGraph) -> list[str]:
    """Return a list of structural problems (empty == valid). Used by checkers."""
    issues: list[str] = []
    ids = set()
    for n in kg.nodes:
        if n.kind not in KG_KINDS:
            issues.append(f"node {n.id}: bad kind {n.kind!r}")
        if not n.title:
            issues.append(f"node {n.id}: empty title")
        ids.add(n.id)
    for e in kg.edges:
        if e.src not in ids:
            issues.append(f"edge dangling src {e.src}")
        if e.dst not in ids:
            issues.append(f"edge dangling dst {e.dst}")
    return issues
