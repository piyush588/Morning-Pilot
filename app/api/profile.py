"""Profile API routes."""

from fastapi import APIRouter

from app.core.db import load_profile, save_profile
from app.models.profile import UserProfile, ProfileUpdateRequest

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("")
async def get_profile(user_id: str = "demo-user") -> UserProfile:
    """Return the full user profile with interests and recent updates."""
    return load_profile(user_id)


@router.put("")
async def update_profile(body: ProfileUpdateRequest, user_id: str = "demo-user"):
    """Update user name and/or interests."""
    profile = load_profile(user_id)

    if body.name:
        profile.name = body.name
    if body.interests:
        profile.interests = body.interests

    save_profile(profile)
    return {"status": "updated", "interests": profile.interests}


@router.get("/interests")
async def get_interests(user_id: str = "demo-user"):
    """Return just the interest list with 'why' annotations and recent changes."""
    profile = load_profile(user_id)
    return {
        "interests": [i.model_dump() for i in profile.interests],
        "recent_updates": [u.model_dump(mode="json") for u in profile.recent_updates[:10]],
    }
