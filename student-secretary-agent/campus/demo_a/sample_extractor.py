"""Pure heuristic extraction of a sample proposal's section columns + tone (A-Q1).

No LLM: scans for markdown headings and Chinese/numeric/bracket section markers.
The column set feeds the Planner (sample-format constraints) and the Reviewer's
format-adherence checker (checkers.check_format_adherence).
"""
from __future__ import annotations
import re

from campus.demo_a.types import SampleSpec

_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
_CN_NUM_RE = re.compile(r"^\s{0,3}([一二三四五六七八九十百]{1,3})[、.．]\s*(.+)$")
_AR_NUM_RE = re.compile(r"^\s{0,3}(\d{1,2})[\.、)]\s+([^\d].+)$")
_BRACKET_RE = re.compile(r"^\s{0,3}[【\[](.+?)[】\]]\s*$")

_TONE_KEYWORDS = {
    "formal": ["正式", "学术", "academic", "formal", "规范", "严谨"],
    "casual": ["活泼", "亲切", "casual", "轻松", "口语"],
    "persuasive": ["倡议", "呼吁", "号召", "persuasive"],
}


def _candidate_heading(line: str):
    for rx in (_HEADING_RE, _CN_NUM_RE, _AR_NUM_RE, _BRACKET_RE):
        m = rx.match(line)
        if m:
            return m.group(m.lastindex).strip()
    return None


def extract_columns(text: str) -> list[str]:
    cols: list[str] = []
    for line in text.splitlines():
        h = _candidate_heading(line)
        if h and 2 <= len(h) <= 40 and h not in cols:
            cols.append(h)
    return cols


def detect_tone(text: str) -> str:
    low = text.lower()
    for tone, kws in _TONE_KEYWORDS.items():
        if any(kw.lower() in low for kw in kws):
            return tone
    return "formal"


def extract_sample(text: str) -> SampleSpec:
    return SampleSpec(raw=text, columns=extract_columns(text),
                      tone=detect_tone(text))
