"""Briefing models — stories, scripts, and responses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Source(BaseModel):
    """A web source backing a story or answer."""

    title: str
    url: str
    snippet: str | None = None
    fetched_at: datetime | None = None


class Story(BaseModel):
    """A single news story in a briefing."""

    headline: str
    summary: str
    sources: list[Source] = []
    interest_match: str  # which interest this matched
    rank: int
    why: str  # "why this story" for transparency


class BriefingRequest(BaseModel):
    """Optional overrides when triggering a briefing."""

    user_id: str = "demo-user"
    max_stories: int = 5
    max_duration_seconds: int = 300


class BriefingResponse(BaseModel):
    """Full briefing result returned by the API."""

    briefing_id: str
    status: Literal["generating", "completed", "failed"] = "generating"
    audio_url: str | None = None
    duration_seconds: float | None = None
    stories: list[Story] = []
    script: str | None = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
