"""Simple JSON-file database for MVP. No auth, single user."""

import json
import os
from datetime import datetime
from pathlib import Path

from app.models.profile import UserProfile, Interest

DATA_DIR = Path(__file__).parent.parent / "data"
PROFILES_DIR = DATA_DIR / "profiles"
BRIEFINGS_DIR = DATA_DIR / "briefings"
CACHE_DIR = DATA_DIR / "cache"


def _ensure_dirs():
    """Create data directories if they don't exist."""
    for d in [PROFILES_DIR, BRIEFINGS_DIR, CACHE_DIR]:
        d.mkdir(parents=True, exist_ok=True)


_ensure_dirs()


def _profile_path(user_id: str = "demo-user") -> Path:
    return PROFILES_DIR / f"{user_id}.json"


def load_profile(user_id: str = "demo-user") -> UserProfile:
    """Load a user profile from disk, or create a default one."""
    path = _profile_path(user_id)
    if path.exists():
        data = json.loads(path.read_text())
        return UserProfile(**data)

    # Create default profile
    profile = UserProfile(
        user_id=user_id,
        name="Piyush",
        interests=[
            Interest(topic="AI", score=8, source="manual", reason="Selected at signup"),
            Interest(topic="Cricket", score=7, source="manual", reason="Selected at signup"),
            Interest(topic="Startups", score=6, source="manual", reason="Selected at signup"),
            Interest(topic="Markets", score=5, source="manual", reason="Selected at signup"),
        ],
        created_at=datetime.utcnow(),
    )
    save_profile(profile)
    return profile


def save_profile(profile: UserProfile):
    """Persist a user profile to disk."""
    _ensure_dirs()
    path = _profile_path(profile.user_id)
    path.write_text(profile.model_dump_json(indent=2))


def save_briefing_metadata(briefing_id: str, data: dict):
    """Save briefing metadata JSON alongside the audio file."""
    _ensure_dirs()
    path = BRIEFINGS_DIR / f"{briefing_id}.json"
    path.write_text(json.dumps(data, indent=2, default=str))


def load_briefing_metadata(briefing_id: str) -> dict | None:
    """Load briefing metadata by ID."""
    path = BRIEFINGS_DIR / f"{briefing_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def get_latest_briefing_id(user_id: str = "demo-user") -> str | None:
    """Find the most recent briefing for a user."""
    _ensure_dirs()
    briefings = sorted(BRIEFINGS_DIR.glob("*.json"), reverse=True)
    for b in briefings:
        data = json.loads(b.read_text())
        if data.get("user_id", "demo-user") == user_id:
            return b.stem
    return None
