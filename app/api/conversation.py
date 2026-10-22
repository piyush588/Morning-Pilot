"""Conversation / Voice Q&A routes."""

from fastapi import APIRouter, UploadFile, File, Form

from app.core.db import load_profile, load_briefing_metadata
from app.models.conversation import AskRequest, AskResponse, ToolUsed
from app.models.briefing import Source
from app.services import search as search_svc
from app.services import fetch as fetch_svc
from app.services import web_agent as agent_svc
from app.services import llm as llm_svc
from app.services import tts as tts_svc
from app.services import stt as stt_svc
from app.services.profile_engine import boost_interest, extract_topic_from_question

router = APIRouter(prefix="/api/conversation", tags=["conversation"])


@router.post("/ask")
async def ask_text(body: AskRequest) -> AskResponse:
    """Answer a text question about the current briefing.

    Pipeline:
      1. Load briefing context
      2. Search for more info via TinyFish
      3. Fetch the top result
      4. Optionally run Web Agent for verification
      5. Answer via LLM with sources
      6. Generate audio answer
      7. Update user interests
    """
    # Load briefing context
    briefing_data = load_briefing_metadata(body.briefing_id)
    briefing_script = briefing_data.get("script", "") if briefing_data else ""

    tools_used: list[ToolUsed] = []
    context_articles: list[dict] = []
    sources: list[Source] = []

    # 1. Search for more info
    try:
        search_results = await search_svc.search(
            query=body.question,
            purpose=f"Finding more information to answer: {body.question}",
        )
        tools_used.append(
            ToolUsed(tool="tinyfish_search", query=body.question)
        )

        # 2. Fetch top results
        if search_results:
            top_urls = [r["url"] for r in search_results[:3] if r.get("url")]
            if top_urls:
                fetched = await fetch_svc.fetch_urls(
                    top_urls,
                    purpose=f"Getting article details to answer: {body.question}",
                )
                for f_result in fetched:
                    if not f_result.get("error"):
                        context_articles.append(f_result)
                        sources.append(
                            Source(
                                title=f_result.get("title", ""),
                                url=f_result.get("url", ""),
                                snippet=f_result.get("text", "")[:200],
                            )
                        )
                tools_used.append(
                    ToolUsed(tool="tinyfish_fetch", url=", ".join(top_urls[:2]))
                )

        # 3. Web Agent for verification (on the first source)
        if context_articles:
            try:
                research = await agent_svc.research_topic(
                    topic=body.question,
                    url=context_articles[0].get("url", ""),
                )
                if research.get("findings"):
                    context_articles.append(
                        {
                            "title": f"Web Agent Research: {body.question}",
                            "url": context_articles[0].get("url", ""),
                            "text": research["findings"],
                        }
                    )
                tools_used.append(
                    ToolUsed(
                        tool="tinyfish_web_agent",
                        action=f"Researched: {body.question}",
                        url=context_articles[0].get("url", ""),
                    )
                )
            except Exception as e:
                print(f"[Conversation] Web Agent failed (non-fatal): {e}")

    except Exception as e:
        print(f"[Conversation] Search/Fetch failed: {e}")

    # 4. Generate answer via LLM
    answer_text = await llm_svc.answer_question(
        question=body.question,
        briefing_script=briefing_script,
        context_articles=context_articles,
    )

    # 5. Generate audio answer
    answer_audio_url = None
    try:
        audio_bytes = await tts_svc.text_to_speech_bytes(answer_text)
        # Save to a temp file
        import uuid
        audio_id = f"a-{uuid.uuid4().hex[:8]}"
        from app.core.db import BRIEFINGS_DIR
        audio_path = BRIEFINGS_DIR / f"{audio_id}.mp3"
        audio_path.write_bytes(audio_bytes)
        answer_audio_url = f"/api/briefing/{audio_id}/audio"
    except Exception as e:
        print(f"[Conversation] TTS for answer failed: {e}")

    # 6. Update interests
    profile_update = None
    topic = extract_topic_from_question(body.question)
    if topic:
        profile = load_profile()
        profile_update = boost_interest(profile, topic, delta=2.0, trigger="question")

    return AskResponse(
        answer_text=answer_text,
        answer_audio_url=answer_audio_url,
        sources=sources,
        tools_used=tools_used,
        profile_update=profile_update,
    )


@router.post("/ask-voice")
async def ask_voice(
    briefing_id: str = Form(...),
    audio: UploadFile = File(...),
) -> AskResponse:
    """Accept an audio question, transcribe it, and answer.

    Same pipeline as /ask but starts with STT.
    """
    # Transcribe
    audio_bytes = await audio.read()
    question = await stt_svc.speech_to_text(audio_bytes)

    # Delegate to text Q&A
    return await ask_text(
        AskRequest(briefing_id=briefing_id, question=question)
    )
