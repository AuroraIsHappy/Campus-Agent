"""Review mind-map builder (Phase 9 — GOAL.md 复习思维导图).

Turns a ``KnowledgeGraph`` into a mind map. The KG's edges are all
``rel="contains"`` (chapter → concept/formula/...), forming a forest of
chapter-rooted trees — which maps directly onto a mind map.

Outputs three representations from the same builder (zero new deps):
- ``tree``: nested ``{title, kind, summary, children:[...]}`` JSON tree.
- ``markdown``: nested Markdown bullet list (renders in any markdown viewer).
- ``mermaid``: Mermaid ``mindmap`` syntax (renders in Notion/GitHub/most editors).

Pure function — no I/O, no clock. The pipeline writes these to the run dir.
"""
from __future__ import annotations
import json
from typing import Any, Optional

from campus.demo_b.types import KnowledgeGraph

__all__ = ["build_mindmap"]


def _children_of(kg: KnowledgeGraph, node_id: str) -> list[str]:
    """Return dst node ids that ``node_id`` contains."""
    return [e.dst for e in kg.edges if e.src == node_id and e.rel == "contains"]


def _node_by_id(kg: KnowledgeGraph, node_id: str):
    for n in kg.nodes:
        if n.id == node_id:
            return n
    return None


def _build_tree(kg: KnowledgeGraph, node_id: str, seen: set[str]) -> Optional[dict[str, Any]]:
    """Recursively build a subtree rooted at ``node_id``. Guards against cycles."""
    if node_id in seen:
        return None
    seen.add(node_id)
    node = _node_by_id(kg, node_id)
    if node is None:
        return None
    children: list[dict[str, Any]] = []
    for cid in _children_of(kg, node_id):
        child = _build_tree(kg, cid, seen)
        if child is not None:
            children.append(child)
    return {
        "title": node.title,
        "kind": node.kind,
        "summary": node.summary,
        "children": children,
    }


def build_mindmap(kg: KnowledgeGraph) -> dict[str, str]:
    """Build mind-map representations from a KnowledgeGraph.

    Returns ``{"tree": <json str>, "markdown": <str>, "mermaid": <str>}``.

    Roots are chapter nodes (or all top-level nodes if no chapters exist).
    Orphan nodes (no incoming edge) that aren't chapters become their own roots.
    """
    # find roots: chapters, plus any node with no incoming "contains" edge
    contained = {e.dst for e in kg.edges if e.rel == "contains"}
    roots = [n.id for n in kg.nodes
             if n.id not in contained and (n.kind == "chapter" or True)]
    # prefer chapters as roots; if chapters exist, only they are roots
    chapter_ids = [n.id for n in kg.nodes if n.kind == "chapter"]
    if chapter_ids:
        roots = chapter_ids

    trees: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rid in roots:
        if rid in seen:
            continue
        t = _build_tree(kg, rid, seen)
        if t is not None:
            trees.append(t)
    # any nodes not yet placed → flat roots
    for n in kg.nodes:
        if n.id not in seen:
            trees.append({"title": n.title, "kind": n.kind,
                          "summary": n.summary, "children": []})

    tree = {"title": "复习思维导图", "kind": "root", "summary": "", "children": trees}

    return {
        "tree": json.dumps(tree, ensure_ascii=False, indent=2),
        "markdown": _tree_to_markdown(tree, depth=0),
        "mermaid": _tree_to_mermaid(tree),
    }


def _tree_to_markdown(node: dict[str, Any], depth: int) -> str:
    """Nested Markdown bullet list."""
    indent = "  " * depth
    bullet = "-" if depth > 0 else "#"
    title = node.get("title", "")
    kind = node.get("kind", "")
    kind_tag = f" *({kind})*" if kind and kind != "root" else ""
    summary = node.get("summary", "")
    line = f"{indent}{bullet} {title}{kind_tag}"
    if summary and depth > 0:
        line += f" — {summary[:120]}"
    lines = [line]
    for child in node.get("children", []):
        lines.append(_tree_to_markdown(child, depth + 1))
    return "\n".join(l for l in lines if l)


def _mermaid_id(title: str) -> str:
    """Sanitize a title into a mermaid-safe node id."""
    import re
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "_", title).strip("_")
    return s or "node"


def _tree_to_mermaid(node: dict[str, Any]) -> str:
    """Mermaid ``mindmap`` syntax.

    Mermaid mindmap uses indentation to denote hierarchy. We emit the root
    followed by indented children.
    """
    lines = ["mindmap"]
    _emit_mermaid(node, lines, depth=1)
    return "\n".join(lines)


def _emit_mermaid(node: dict[str, Any], lines: list[str], depth: int) -> None:
    indent = "  " * depth
    title = node.get("title", "")
    kind = node.get("kind", "")
    shape = ""
    if kind == "chapter":
        shape = f"[{title}]"
    elif kind == "formula":
        shape = f"(({title}))"
    elif kind == "key_point":
        shape = f"{{ {title} }}"
    else:
        shape = title
    lines.append(f"{indent}{shape}")
    for child in node.get("children", []):
        _emit_mermaid(child, lines, depth + 1)
