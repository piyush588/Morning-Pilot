"""Health check endpoint."""

from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check():
    """Check that all external services are configured."""
    return {
        "status": "ok",
        "services": {
            "tinyfish": "configured" if settings.tinyfish_api_key else "missing_key",
            "elevenlabs": "configured" if settings.elevenlabs_api_key else "missing_key",
            "llm": "configured" if settings.openai_api_key else "missing_key",
        },
        "scheduler": {
            "briefing_hour": settings.briefing_schedule_hour,
        },
    }
