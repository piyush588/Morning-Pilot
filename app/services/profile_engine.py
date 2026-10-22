"""Profile engine — interest scoring, updates, and decay."""

from datetime import datetime

from app.models.profile import Interest, InterestUpdate, UserProfile
from app.core.db import load_profile, save_profile


def boost_interest(
    profile: UserProfile,
    topic: str,
    delta: float = 2.0,
    trigger: str = "question",
) -> InterestUpdate:
    """Boost or add an interest based on user behavior.

    Returns the InterestUpdate record for UI display.
    """
    existing = next((i for i in profile.interests if i.topic.lower() == topic.lower()), None)

    if existing:
        old_score = existing.score
        existing.score = min(10, existing.score + delta)
        update = InterestUpdate(
            action="boosted",
            topic=existing.topic,
            delta=f"+{delta}",
            trigger=trigger,
            timestamp=datetime.utcnow(),
        )
    else:
        new_interest = Interest(
            topic=topic,
            score=min(10, delta + 1),
            source="question" if trigger == "question" else "inferred",
            reason=f"{'Asked about' if trigger == 'question' else 'Inferred from'}: {topic}",
        )
        profile.interests.append(new_interest)
        update = InterestUpdate(
            action="added",
            topic=topic,
            delta=f"+{delta + 1}",
            trigger=trigger,
            timestamp=datetime.utcnow(),
        )

    profile.recent_updates.insert(0, update)
    # Keep only last 20 updates
    profile.recent_updates = profile.recent_updates[:20]

    save_profile(profile)
    return update


def decay_interests(profile: UserProfile, factor: float = 0.95):
    """Apply daily decay to all interests. Called before each briefing.

    Interests below 1.0 are removed.
    """
    remaining = []
    for interest in profile.interests:
        interest.score *= factor
        if interest.score >= 1.0:
            remaining.append(interest)
        else:
            profile.recent_updates.insert(
                0,
                InterestUpdate(
                    action="decayed",
                    topic=interest.topic,
                    delta=f"-{interest.topic}",
                    trigger="decay",
                    timestamp=datetime.utcnow(),
                ),
            )
    profile.interests = remaining
    save_profile(profile)


def extract_topic_from_question(question: str) -> str | None:
    """Heuristic: extract a probable topic from a user question.

    For MVP, we just look for keywords. A production version would use the LLM.
    """
    # Common news topics to match against
    known_topics = [
        "AI", "cricket", "startups", "markets", "RBI", "politics",
        "technology", "sports", "economy", "climate", "health",
        "education", "space", "crypto", "bitcoin", "IPO", "election",
    ]

    question_lower = question.lower()
    for topic in known_topics:
        if topic.lower() in question_lower:
            return topic

    # Fallback: use the main noun phrase (first 2-3 significant words)
    words = [w for w in question.split() if len(w) > 3 and w.lower() not in {
        "what", "about", "more", "tell", "deeper", "explain", "that", "this",
        "could", "would", "should", "does", "have", "been", "with", "from",
        "into", "they", "their", "there", "here", "when", "where", "which",
    }]
    if words:
        return " ".join(words[:2]).title()
    return None
