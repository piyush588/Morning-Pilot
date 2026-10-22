"""Conversation / Q&A models."""

from pydantic import BaseModel

from app.models.briefing import Source
from app.models.profile import InterestUpdate


class ToolUsed(BaseModel):
    """Record of a TinyFish tool call for transparency in the UI."""

    tool: str  # "tinyfish_search", "tinyfish_fetch", "tinyfish_web_agent"
    query: str | None = None
    url: str | None = None
    action: str | None = None


class AskRequest(BaseModel):
    """Text-mode question about the current briefing."""

    briefing_id: str
    question: str


class AskResponse(BaseModel):
    """Answer with sources, tools used, and profile side-effects."""

    answer_text: str
    answer_audio_url: str | None = None
    sources: list[Source] = []
    tools_used: list[ToolUsed] = []
    profile_update: InterestUpdate | None = None
