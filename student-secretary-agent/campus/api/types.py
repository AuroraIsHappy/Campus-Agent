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


class MemoryQuery(BaseModel):
    query: str
    k: int = 5


class OnboardingRequest(BaseModel):
    answers: dict[str, str] = {}


class PushRequest(BaseModel):
    channel: str = "feishu"
    target: Optional[str] = None
    message: str
