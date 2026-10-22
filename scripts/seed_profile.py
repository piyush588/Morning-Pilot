"""Seed a demo user profile with default interests."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from app.core.db import save_profile
from app.models.profile import UserProfile, Interest


def main():
    profile = UserProfile(
        user_id="demo-user",
        name="Piyush",
        interests=[
            Interest(topic="AI", score=10, source="manual", reason="Selected at signup"),
            Interest(topic="Cricket", score=8, source="manual", reason="Selected at signup"),
            Interest(topic="Startups", score=7, source="manual", reason="Selected at signup"),
            Interest(topic="Markets", score=6, source="manual", reason="Selected at signup"),
        ],
        created_at=datetime.now(timezone.utc),
    )
    save_profile(profile)
    print(f"✅ Demo profile created for '{profile.name}' with {len(profile.interests)} interests")
    print(f"   Topics: {', '.join(i.topic for i in profile.interests)}")


if __name__ == "__main__":
    main()
