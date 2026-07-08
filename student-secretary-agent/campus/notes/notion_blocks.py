"""Markdown → Notion block objects (Phase 9 — GOAL.md 讲义导出到 Notion).

Converts a Markdown string into a list of Notion block objects so the lecture
pipeline can export the full knowledge graph + review plan + mind map into one
rich Notion page (not just a single summary paragraph).

Notion API constraints honored:
- Max 100 blocks per ``POST /v1/pages`` (we cap + warn).
- Max 2000 chars per rich_text text node (we split long paragraphs).
- Supported block types: heading_1/2/3, paragraph, bulleted_list_item,
  numbered_list_item, code, quote, divider, table.

Pure function — no I/O, no network.
"""
from __future__ import annotations
import re
from typing import Any

__all__ = ["markdown_to_notion_blocks", "MAX_BLOCKS", "MAX_CHARS"]

MAX_BLOCKS = 100
MAX_CHARS = 2000


def _text_nodes(text: str) -> list[dict[str, Any]]:
    """Split text into ≤2000-char rich_text nodes (Notion hard limit per node)."""
    text = text or ""
    nodes = []
    for i in range(0, len(text), MAX_CHARS):
        nodes.append({"type": "text", "text": {"content": text[i:i + MAX_CHARS]}})
    return nodes


def _rich_text(text: str) -> list[dict[str, Any]]:
    """Build a rich_text array. Notion requires at least one node for text blocks."""
    nodes = _text_nodes(text)
    return nodes or [{"type": "text", "text": {"content": ""}}]


def markdown_to_notion_blocks(md: str) -> list[dict[str, Any]]:
    """Convert a Markdown string into Notion block objects.

    Handles: H1-H3 (``#``/``##``/``###``), bulleted lists (``-``/``*``),
    numbered lists (``1.``), code fences (``` ```), blockquotes (``>``),
    tables (pipe syntax), and plain paragraphs. Unknown lines → paragraph.
    """
    if not md:
        return []
    lines = md.split("\n")
    blocks: list[dict[str, Any]] = []
    i = 0
    n = len(lines)
    while i < n:
        if len(blocks) >= MAX_BLOCKS:
            blocks.append({"object": "block", "type": "paragraph",
                           "paragraph": {"rich_text": _rich_text(
                               "…（内容超过 100 块上限，已截断）")}})
            break
        line = lines[i]
        stripped = line.strip()

        # skip empty
        if not stripped:
            i += 1
            continue

        # code fence
        if stripped.startswith("```"):
            code_lines = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            blocks.append({"object": "block", "type": "code",
                           "code": {"rich_text": _rich_text("\n".join(code_lines)),
                                    "language": "plain text"}})
            continue

        # headings
        m = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            btype = {1: "heading_1", 2: "heading_2", 3: "heading_3"}[level]
            blocks.append({"object": "block", "type": btype,
                           btype: {"rich_text": _rich_text(text)}})
            i += 1
            continue

        # blockquote
        if stripped.startswith(">"):
            text = stripped.lstrip("> ").strip()
            blocks.append({"object": "block", "type": "quote",
                           "quote": {"rich_text": _rich_text(text)}})
            i += 1
            continue

        # table (pipe syntax)
        if "|" in stripped and i + 1 < n and re.match(r"^\s*\|?[\s\-:|]+\|?\s*$", lines[i + 1]):
            table_rows = []
            i += 2  # skip header + separator
            while i < n and "|" in lines[i].strip():
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                table_rows.append(cells)
                i += 1
            if table_rows:
                ncols = len(table_rows[0])
                blocks.append(_table_block(table_rows, ncols))
            continue

        # numbered list
        m = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if m:
            text = m.group(2).strip()
            blocks.append({"object": "block", "type": "numbered_list_item",
                           "numbered_list_item": {"rich_text": _rich_text(text)}})
            i += 1
            continue

        # bulleted list
        m = re.match(r"^[-*]\s+(.+)$", stripped)
        if m:
            text = m.group(1).strip()
            blocks.append({"object": "block", "type": "bulleted_list_item",
                           "bulleted_list_item": {"rich_text": _rich_text(text)}})
            i += 1
            continue

        # plain paragraph
        blocks.append({"object": "block", "type": "paragraph",
                       "paragraph": {"rich_text": _rich_text(stripped)}})
        i += 1

    return blocks


def _table_block(rows: list[list[str]], ncols: int) -> dict[str, Any]:
    """Build a Notion table block (table_row children)."""
    children = []
    for row in rows[:MAX_BLOCKS]:
        cells = [row[j] if j < len(row) else "" for j in range(ncols)]
        children.append({"object": "block", "type": "table_row",
                         "table_row": {"cells": [[{"type": "text",
                                                    "text": {"content": c[:MAX_CHARS]}}]
                                                   for c in cells]}})
    return {"object": "block", "type": "table",
            "table": {"table_width": ncols, "has_column_header": True,
                      "has_row_header": False, "children": children}}
