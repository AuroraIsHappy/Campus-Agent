"""Demo A data types (social-practice proposal + outreach + email)."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class SampleSpec:
    """A user-supplied sample proposal, parsed into format signals (A-Q1)."""
    raw: str = ""
    columns: list[str] = field(default_factory=list)  # section/heading names
    tone: str = ""                                     # formal/casual/persuasive
    constraints: list[str] = field(default_factory=list)


@dataclass
class Brief:
    """The user's short brief: topic / region / time window."""
    topic: str = ""
    region: str = ""
    window: str = ""


@dataclass
class OutreachTarget:
    name: str = ""
    visit_reason: str = ""
    contact_source: str = ""   # where contact info came from (a URL)
    url: str = ""
    score: float = 0.0


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class RunResult:
    ok: bool
    run_dir: str
    final_status: str = ""
    outreach_count: int = 0
    email_segments: int = 0
    checks: list[CheckResult] = field(default_factory=list)
    debates: list[dict] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    error: str = ""
