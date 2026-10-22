"""User profile and interest models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Interest(BaseModel):
    """A single interest topic with its score and provenance."""

    topic: str
    score: float = Field(ge=0, le=10, description="Interest strength, 1-10")
    source: Literal["manual", "inferred", "question"] = "manual"
    reason: str | None = None


class InterestUpdate(BaseModel):
    """A record of a single interest change, shown in the UI."""

    action: Literal["boosted", "added", "decayed", "removed"]
    topic: str
    delta: str  # "+2", "-1"
    trigger: str  # "question", "skip", "more_of_this", "signup"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UserProfile(BaseModel):
    """Complete user profile stored on disk / in DB."""

    user_id: str = "demo-user"
    name: str = "User"
    interests: list[Interest] = []
    recent_updates: list[InterestUpdate] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    briefings_generated: int = 0


class ProfileUpdateRequest(BaseModel):
    """Request body for PUT /api/profile."""

    name: str | None = None
    interests: list[Interest] = []
