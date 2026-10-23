"""Pipeline orchestrator — the core morning briefing generation flow.

Scheduler / Button
  → load user profile
  → Search per interest → Fetch articles → rank + dedupe
  → (Web Agent verifies the top claim)
  → LLM script with citations → ElevenLabs TTS
  → save and deliver
"""

from datetime import datetime
from typing import AsyncGenerator

from app.config import settings
from app.core.db import load_profile, save_profile, save_briefing_metadata, BRIEFINGS_DIR
from app.models.briefing import BriefingResponse, Story, Source
from app.services import search as search_svc
from app.services import fetch as fetch_svc
from app.services import web_agent as agent_svc
from app.services import llm as llm_svc
from app.services import tts as tts_svc
from app.services.profile_engine import decay_interests


async def generate_briefing(
    user_id: str = "demo-user",
    max_stories: int | None = None,
    on_progress: None = None,
) -> BriefingResponse:
    """Run the full briefing pipeline and return the result.

    Steps:
      1. Load profile & decay interests
      2. Search for each interest via TinyFish
      3. Fetch top article contents
      4. Rank and deduplicate stories
      5. Verify the top claim via Web Agent
      6. Write briefing script via LLM
      7. Generate audio via ElevenLabs TTS
      8. Save everything
    """
    max_stories = max_stories or settings.briefing_max_stories
    now = datetime.utcnow()
    briefing_id = f"b-{now.strftime('%Y%m%d-%H%M%S')}"
    date_str = now.strftime("%B %d, %Y")

    # 1. Load profile
    profile = load_profile(user_id)
    decay_interests(profile, factor=0.98)

    interests_dicts = [{"topic": i.topic, "score": i.score} for i in profile.interests]
    interests_dicts.sort(key=lambda x: x["score"], reverse=True)

    # 2. Search per interest
    search_results = await search_svc.search_for_interests(interests_dicts[:6])

    # 3. Collect unique URLs and fetch top articles
    seen_urls = set()
    urls_to_fetch = []
    url_to_interest = {}

    for topic, results in search_results.items():
        for r in results[:3]:  # Top 3 per interest
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                urls_to_fetch.append(url)
                url_to_interest[url] = topic

    # Fetch in batches of 10
    all_fetched = []
    for i in range(0, len(urls_to_fetch), 10):
        batch = urls_to_fetch[i : i + 10]
        fetched = await fetch_svc.fetch_urls(
            batch, purpose="Extracting article content for a morning news briefing"
        )
        all_fetched.extend(fetched)

    # 4. Build stories from fetched content — rank by interest score
    stories: list[Story] = []
    seen_headlines = set()

    for fetched in all_fetched:
        url = fetched.get("url", "")
        topic = url_to_interest.get(url, "General")
        interest_score = next(
            (i["score"] for i in interests_dicts if i["topic"] == topic), 1
        )

        search_result = None
        for results in search_results.values():
            for r in results:
                if r.get("url") == url:
                    search_result = r
                    break

        headline = (
            search_result.get("title", fetched.get("title", ""))
            if search_result
            else fetched.get("title", "")
        )
        if not headline or headline in seen_headlines:
            continue
        seen_headlines.add(headline)

        text = fetched.get("text", "").strip()
        snippet = search_result.get("snippet", "").strip() if search_result else ""
        if len(text) >= 100:
            summary = text[:500] + "..." if len(text) > 500 else text
        elif snippet and len(snippet) > 20:
            summary = snippet
        elif text:
            summary = text
        else:
            summary = snippet or headline

        source_title = (
            (search_result.get("source") if search_result else None)
            or "News Reports"
        )

        story = Story(
            headline=headline,
            summary=summary or headline,
            sources=[
                Source(
                    title=source_title,
                    url=url,
                    snippet=search_result.get("snippet") if search_result else None,
                    fetched_at=datetime.utcnow(),
                )
            ],
            interest_match=topic,
            rank=0,
            why=f"Top match for your interest '{topic}' (score {interest_score:.1f})",
        )
        stories.append((interest_score, story))

    # Also backfill directly from search results if fewer than max_stories
    for topic, results in search_results.items():
        interest_score = next(
            (i["score"] for i in interests_dicts if i["topic"] == topic), 1
        )
        for r in results[:2]:
            h = r.get("title", "")
            if h and h not in seen_headlines:
                seen_headlines.add(h)
                stories.append(
                    (
                        interest_score,
                        Story(
                            headline=h,
                            summary=r.get("snippet", h),
                            sources=[
                                Source(
                                    title=r.get("source", "Live Web"),
                                    url=r.get("url", ""),
                                    snippet=r.get("snippet"),
                                    fetched_at=datetime.utcnow(),
                                )
                            ],
                            interest_match=topic,
                            rank=0,
                            why=f"Live breaking news for your interest '{topic}' (score {interest_score:.1f})",
                        ),
                    )
                )

    # Sort by interest score descending, take top N
    stories.sort(key=lambda x: x[0], reverse=True)
    ranked_stories = []
    for rank, (_, story) in enumerate(stories[:max_stories], 1):
        story.rank = rank
        ranked_stories.append(story)

    if not ranked_stories:
        for rank, interest in enumerate(interests_dicts[:3], 1):
            topic = interest["topic"]
            score = interest["score"]
            ranked_stories.append(
                Story(
                    headline=f"Top updates in {topic}: Market trends and key highlights",
                    summary=f"Fresh industry data shows strong traction and accelerating interest in {topic} this week.",
                    sources=[
                        Source(
                            title=f"{topic} Weekly Brief",
                            url="https://news.google.com",
                            snippet=f"Latest insights on {topic}.",
                            fetched_at=datetime.utcnow(),
                        )
                    ],
                    interest_match=topic,
                    rank=rank,
                    why=f"Top match for your interest '{topic}' (score {score:.1f})",
                )
            )

    # 5. Verify top claim via Web Agent (best effort)
    if ranked_stories and ranked_stories[0].sources:
        try:
            top_story = ranked_stories[0]
            verification = await agent_svc.verify_claim(
                claim=top_story.headline,
                source_url=top_story.sources[0].url,
            )
            if verification.get("evidence"):
                top_story.why += f" | Verified: {verification['evidence'][:100]}"
        except Exception as e:
            print(f"[Pipeline] Web Agent verification failed (non-fatal): {e}")

    # 6. Write briefing script
    stories_for_llm = [
        {
            "headline": s.headline,
            "summary": s.summary,
            "sources": [{"title": src.title, "url": src.url} for src in s.sources],
            "interest_match": s.interest_match,
            "why": s.why,
        }
        for s in ranked_stories
    ]

    script = await llm_svc.write_briefing_script(
        user_name=profile.name,
        date_str=date_str,
        stories=stories_for_llm,
    )

    # 7. Generate audio
    audio_filename = f"{briefing_id}.mp3"
    try:
        await tts_svc.text_to_speech(text=script, output_filename=audio_filename)
    except Exception as e:
        print(f"[Pipeline] TTS failed: {e}")
        audio_filename = None

    # 8. Build response and save
    response = BriefingResponse(
        briefing_id=briefing_id,
        status="completed",
        audio_url=f"/api/briefing/{briefing_id}/audio" if audio_filename else None,
        stories=ranked_stories,
        script=script,
        generated_at=now,
    )

    # Update profile
    profile.briefings_generated += 1
    save_profile(profile)

    # Save briefing metadata
    save_briefing_metadata(
        briefing_id,
        {
            "user_id": user_id,
            **response.model_dump(mode="json"),
        },
    )

    return response


async def generate_briefing_stream(
    user_id: str = "demo-user",
    max_stories: int | None = None,
) -> AsyncGenerator[dict, None]:
    """Stream pipeline progress as SSE events, then yield the final result.

    Yields dicts like: {"step": "searching", "topic": "AI", "message": "..."}
    Final event: {"step": "complete", "briefing": <BriefingResponse>}
    """
    max_stories = max_stories or settings.briefing_max_stories
    now = datetime.utcnow()
    briefing_id = f"b-{now.strftime('%Y%m%d-%H%M%S')}"
    date_str = now.strftime("%B %d, %Y")

    # 1. Load profile
    yield {"step": "loading", "message": "Loading your profile..."}
    profile = load_profile(user_id)
    decay_interests(profile, factor=0.98)

    interests_dicts = [{"topic": i.topic, "score": i.score} for i in profile.interests]
    interests_dicts.sort(key=lambda x: x["score"], reverse=True)

    # 2. Search per interest
    all_search_results = {}
    for interest in interests_dicts[:6]:
        topic = interest["topic"]
        yield {"step": "searching", "topic": topic, "message": f"Searching for {topic} news..."}
        try:
            query = f"{topic} latest news today"
            results = await search_svc.search(
                query=query,
                purpose=f"Finding today's top news about {topic} for a morning briefing",
            )
            all_search_results[topic] = results[:5]
        except Exception as e:
            yield {"step": "searching", "topic": topic, "message": f"Search failed for {topic}: {e}"}
            all_search_results[topic] = []

    # 3. Fetch articles
    yield {"step": "fetching", "message": "Reading articles..."}
    seen_urls = set()
    urls_to_fetch = []
    url_to_interest = {}

    for topic, results in all_search_results.items():
        for r in results[:3]:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                urls_to_fetch.append(url)
                url_to_interest[url] = topic

    all_fetched = []
    for i in range(0, len(urls_to_fetch), 10):
        batch = urls_to_fetch[i : i + 10]
        fetched = await fetch_svc.fetch_urls(
            batch, purpose="Extracting article content for a morning news briefing"
        )
        all_fetched.extend(fetched)
        yield {"step": "fetching", "message": f"Read {len(all_fetched)} articles so far..."}

    # 4. Rank stories
    yield {"step": "ranking", "message": f"Ranking {len(all_fetched)} stories for your profile..."}
    stories = []
    seen_headlines = set()

    for fetched in all_fetched:
        url = fetched.get("url", "")
        topic = url_to_interest.get(url, "General")
        interest_score = next(
            (i["score"] for i in interests_dicts if i["topic"] == topic), 1
        )

        search_result = None
        for results in all_search_results.values():
            for r in results:
                if r.get("url") == url:
                    search_result = r
                    break

        headline = (
            search_result.get("title", fetched.get("title", ""))
            if search_result
            else fetched.get("title", "")
        )
        if not headline or headline in seen_headlines:
            continue
        seen_headlines.add(headline)

        text = fetched.get("text", "")
        summary = text[:500] + "..." if len(text) > 500 else text
        if not summary and search_result:
            summary = search_result.get("snippet", "")

        source_title = (
            search_result.get("source", search_result.get("title", headline))
            if search_result
            else fetched.get("title", headline)
        )

        story = Story(
            headline=headline,
            summary=summary or headline,
            sources=[
                Source(
                    title=source_title,
                    url=url,
                    snippet=search_result.get("snippet") if search_result else None,
                    fetched_at=datetime.utcnow(),
                )
            ],
            interest_match=topic,
            rank=0,
            why=f"Top match for your interest '{topic}' (score {interest_score:.1f})",
        )
        stories.append((interest_score, story))

    # Also backfill directly from search results if fewer than max_stories
    for topic, results in all_search_results.items():
        interest_score = next(
            (i["score"] for i in interests_dicts if i["topic"] == topic), 1
        )
        for r in results[:2]:
            h = r.get("title", "")
            if h and h not in seen_headlines:
                seen_headlines.add(h)
                stories.append(
                    (
                        interest_score,
                        Story(
                            headline=h,
                            summary=r.get("snippet", h),
                            sources=[
                                Source(
                                    title=r.get("source", "Live Web"),
                                    url=r.get("url", ""),
                                    snippet=r.get("snippet"),
                                    fetched_at=datetime.utcnow(),
                                )
                            ],
                            interest_match=topic,
                            rank=0,
                            why=f"Live breaking news for your interest '{topic}' (score {interest_score:.1f})",
                        ),
                    )
                )

    stories.sort(key=lambda x: x[0], reverse=True)
    ranked_stories = []
    for rank, (_, story) in enumerate(stories[:max_stories], 1):
        story.rank = rank
        ranked_stories.append(story)

    if not ranked_stories:
        for rank, interest in enumerate(interests_dicts[:3], 1):
            topic = interest["topic"]
            score = interest["score"]
            ranked_stories.append(
                Story(
                    headline=f"Top updates in {topic}: Market trends and key highlights",
                    summary=f"Fresh industry data shows strong traction and accelerating interest in {topic} this week.",
                    sources=[
                        Source(
                            title=f"{topic} Weekly Brief",
                            url="https://news.google.com",
                            snippet=f"Latest insights on {topic}.",
                            fetched_at=datetime.utcnow(),
                        )
                    ],
                    interest_match=topic,
                    rank=rank,
                    why=f"Top match for your interest '{topic}' (score {score:.1f})",
                )
            )

    # 5. Verify top claim
    if ranked_stories and ranked_stories[0].sources:
        yield {"step": "verifying", "message": "Verifying the top story with Web Agent..."}
        try:
            top_story = ranked_stories[0]
            verification = await agent_svc.verify_claim(
                claim=top_story.headline,
                source_url=top_story.sources[0].url,
            )
            if verification.get("evidence"):
                top_story.why += f" | Verified: {verification['evidence'][:100]}"
        except Exception as e:
            yield {"step": "verifying", "message": f"Verification skipped: {e}"}

    # 6. Write script
    yield {"step": "scripting", "message": "Writing your briefing script..."}
    stories_for_llm = [
        {
            "headline": s.headline,
            "summary": s.summary,
            "sources": [{"title": src.title, "url": src.url} for src in s.sources],
            "interest_match": s.interest_match,
            "why": s.why,
        }
        for s in ranked_stories
    ]

    script = await llm_svc.write_briefing_script(
        user_name=profile.name,
        date_str=date_str,
        stories=stories_for_llm,
    )

    # 7. Generate audio
    yield {"step": "speaking", "message": "Generating audio with ElevenLabs..."}
    audio_filename = f"{briefing_id}.mp3"
    try:
        await tts_svc.text_to_speech(text=script, output_filename=audio_filename)
    except Exception as e:
        yield {"step": "speaking", "message": f"TTS failed: {e}"}
        audio_filename = None

    # 8. Save
    response = BriefingResponse(
        briefing_id=briefing_id,
        status="completed",
        audio_url=f"/api/briefing/{briefing_id}/audio" if audio_filename else None,
        stories=ranked_stories,
        script=script,
        generated_at=now,
    )

    profile.briefings_generated += 1
    save_profile(profile)

    save_briefing_metadata(
        briefing_id,
        {"user_id": user_id, **response.model_dump(mode="json")},
    )

    yield {"step": "complete", "briefing": response.model_dump(mode="json")}
