"""Briefing API routes — generate, stream, and serve briefings."""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from app.core.db import load_briefing_metadata, get_latest_briefing_id, BRIEFINGS_DIR
from app.models.briefing import BriefingRequest, BriefingResponse
from app.services.pipeline import generate_briefing, generate_briefing_stream

router = APIRouter(prefix="/api/briefing", tags=["briefing"])


@router.post("/generate")
async def trigger_generate(body: BriefingRequest | None = None) -> BriefingResponse:
    """Trigger the full pipeline and return the completed briefing.

    This is the endpoint behind the "Generate my briefing now" button.
    """
    user_id = body.user_id if body else "demo-user"
    max_stories = body.max_stories if body else 5

    result = await generate_briefing(user_id=user_id, max_stories=max_stories)
    return result


@router.post("/generate/stream")
async def trigger_generate_stream(body: BriefingRequest | None = None):
    """Stream pipeline progress via SSE, then emit the final briefing.

    Events:
      event: step  → {"step": "searching", "topic": "AI", "message": "..."}
      event: complete → {"briefing": <BriefingResponse>}
    """
    user_id = body.user_id if body else "demo-user"
    max_stories = body.max_stories if body else 5

    async def event_generator():
        async for event in generate_briefing_stream(
            user_id=user_id, max_stories=max_stories
        ):
            step = event.get("step", "unknown")
            event_type = "complete" if step == "complete" else "step"
            yield f"event: {event_type}\ndata: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/latest")
async def get_latest(user_id: str = "demo-user"):
    """Return the most recent briefing for a user."""
    briefing_id = get_latest_briefing_id(user_id)
    if not briefing_id:
        raise HTTPException(status_code=404, detail="No briefings found")

    data = load_briefing_metadata(briefing_id)
    if not data:
        raise HTTPException(status_code=404, detail="Briefing metadata not found")

    return data


@router.get("/{briefing_id}/audio")
async def get_audio(briefing_id: str):
    """Stream the briefing audio MP3 file."""
    audio_path = BRIEFINGS_DIR / f"{briefing_id}.mp3"
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        filename=f"{briefing_id}.mp3",
    )
