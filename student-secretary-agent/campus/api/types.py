"""Request/response schemas for the Campus API (pydantic v1/v2 compatible)."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class DemoBRequest(BaseModel):
    path: str
    exam_date: str
    free_minutes: int = 300
    start_date: Optional[str] = None
    topic: Optional[str] = None


class DemoARequest(BaseModel):
    sample_text: str = ""
    topic: str = "校园低碳实践"
    region: str = "北京高校社区"
    window: str = "2026 暑期"
    mode: str = "offline"  # offline | auto | real


class DemoCRequest(BaseModel):
    goal: str
    days: int = 30
    minutes: int = 20
    quiz_n: int = 3
    mode: str = "offline"  # offline | auto | real


class AgentRunRequest(BaseModel):
    message: str
    mode: str = "offline"  # offline | auto | real
    context: dict = {}


class MemoryQuery(BaseModel):
    query: str
    k: int = 5


class OnboardingRequest(BaseModel):
    answers: dict[str, str] = {}


class PushRequest(BaseModel):
    channel: str = "feishu"
    target: Optional[str] = None
    message: str


class ResearchTopicRequest(BaseModel):
    title: str
    query: str = ""
    keywords: list[str] = []
    cadence: str = "daily"


class ResearchRefreshRequest(BaseModel):
    mode: str = "offline"


class NotionSyncRequest(BaseModel):
    digest: dict
    mode: str = "local"  # local | notion


class EventRequest(BaseModel):
    title: str
    start: str                       # "2026-07-09T08:00"
    end: Optional[str] = None
    rrule: Optional[str] = None
    location: str = ""
    note: str = ""


class AnniversaryRequest(BaseModel):
    name: str
    date: str                        # "MM-DD"
    kind: str = "birthday"           # birthday | anniversary
    note: str = ""


class LogQuery(BaseModel):
    date: Optional[str] = None       # "YYYY-MM-DD"; defaults to today
    n: int = 7
