"""A-Q1/Q3/Q4 + A-Q2 rule checkers (pure; HTTP via injectable opener).

A-Q1 check_format_adherence : fraction of sample columns present in the proposal.
A-Q3 check_completeness      : budget + timeline + safety sections present (regex).
A-Q4 check_geographic_plaus. : no single date line spans two distant cities.
A-Q2 verify_urls             : HTTP reachability (2xx/3xx) of cited URLs via an
                                injectable opener (tests inject a fake; real run
                                uses urllib). Unreachable -> flag, never fabricate.
"""
from __future__ import annotations
import re

from campus.demo_a.types import CheckResult, OutreachTarget, SampleSpec

_BUDGET_RE = re.compile(r"(预算|经费|budget|费用|支出)")
_TIMELINE_RE = re.compile(r"(时间表|日程|时间安排|行程|timeline|schedule|进度安排)")
_SAFETY_RE = re.compile(r"(安全|应急|预案|保险|risk|safety)")
_DATE_RE = re.compile(
    r"(\d{1,2}月\d{1,2}日|\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}|"
    r"第[一二三四五六七八九十]+天|Day\s*\d+)", re.I)

# City-level only (sub-locations like 博物馆/校区 would cause false positives).
_CITIES = ("北京", "上海", "广州", "深圳", "成都", "武汉", "西安", "杭州",
           "南京", "天津", "重庆", "苏州", "长沙", "郑州", "昆明", "青岛",
           "大连", "厦门", "哈尔滨", "沈阳")


def check_format_adherence(proposal_md: str, sample_spec: SampleSpec,
                           threshold: float = 0.6) -> CheckResult:
    if not sample_spec or not sample_spec.columns:
        return CheckResult("format_adherence", True,
                           "no sample columns to compare")
    present = [c for c in sample_spec.columns if c and c in proposal_md]
    cov = len(present) / len(sample_spec.columns)
    return CheckResult(
        "format_adherence", cov >= threshold,
        f"coverage {cov:.0%} ({len(present)}/{len(sample_spec.columns)}); "
        f"threshold {threshold:.0%}")


def check_completeness(proposal_md: str) -> CheckResult:
    found = {
        "budget": bool(_BUDGET_RE.search(proposal_md)),
        "timeline": bool(_TIMELINE_RE.search(proposal_md)),
        "safety": bool(_SAFETY_RE.search(proposal_md)),
    }
    missing = [k for k, v in found.items() if not v]
    return CheckResult("completeness", not missing,
                       f"sections={found}; missing={missing}")


def _cities_in(line: str) -> list[str]:
    return [c for c in _CITIES if c in line]


def check_geographic_plausibility(proposal_md: str) -> CheckResult:
    """Flag any date-bearing line that mentions >=2 distinct cities (A-Q4)."""
    bad = []
    for line in proposal_md.splitlines():
        if not _DATE_RE.search(line):
            continue
        cities = _cities_in(line)
        if len(set(cities)) >= 2:
            bad.append(line.strip()[:60])
    return CheckResult(
        "geographic_plausibility", not bad,
        f"{len(bad)} date line(s) span multiple cities"
        + ("" if not bad else f": {bad[:3]}"))


def _default_opener(url: str, timeout: float = 5.0) -> int:
    """HTTP reachability of a URL: returns status code (0 on failure). A-Q2."""
    import urllib.request
    headers = {"User-Agent": "campus-demo-a/1.0"}
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return int(getattr(r, "status", r.getcode()))
        except Exception:
            continue
    return 0


def _name_of(t) -> str:
    if isinstance(t, OutreachTarget):
        return t.name
    if isinstance(t, dict):
        return str(t.get("name", ""))
    return ""


def _url_of(t) -> str:
    if isinstance(t, OutreachTarget):
        return t.url
    if isinstance(t, dict):
        return str(t.get("url", ""))
    return ""


def verify_urls(targets, opener=None, timeout: float = 5.0) -> list[dict]:
    """Reachability check for each target.url. opener(url, timeout)->status int.

    Inject ``opener`` in tests to avoid the network. Real run uses urllib.
    """
    open_fn = opener or _default_opener
    out = []
    for t in targets or []:
        url = _url_of(t)
        status = open_fn(url, timeout) if url else 0
        out.append({
            "name": _name_of(t), "url": url, "status": status,
            "reachable": 200 <= status < 400,
        })
    return out
