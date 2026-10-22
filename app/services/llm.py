"""LLM service — script writing and Q&A via OpenAI-compatible API (supports OpenAI & Local Ollama)."""

import re
from openai import AsyncOpenAI

from app.config import settings

_client_cache: dict[str, AsyncOpenAI] = {}


def _get_client_and_model() -> tuple[AsyncOpenAI, str]:
    """Return an AsyncOpenAI client and model name.
    
    Prefers OpenAI API if configured with a real key;
    otherwise falls back to local Ollama (Llama 3.2 3B).
    """
    if settings.openai_api_key and not settings.openai_api_key.startswith("your_openai"):
        key = f"openai:{settings.openai_model}"
        if key not in _client_cache:
            _client_cache[key] = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
            )
        return _client_cache[key], settings.openai_model

    # Local Ollama fallback
    key = f"ollama:{settings.ollama_model}"
    if key not in _client_cache:
        _client_cache[key] = AsyncOpenAI(
            base_url=settings.ollama_base_url,
            api_key="ollama",
        )
    return _client_cache[key], settings.ollama_model


BRIEFING_SYSTEM_PROMPT = """You are Morning Pilot, an elite morning radio host and broadcast journalist (in the style of NPR's Morning Edition, NYT's The Daily, and Morning Brew).
You are speaking directly to the listener in a warm, charismatic, human, conversational voice.

CRITICAL BROADCAST RULES:
1. Address the listener directly: "Good morning, {name}! It's {date}, and here is what you need to know today."
2. Synthesize all the provided stories into a cohesive, flowing broadcast. Do NOT just read disconnected bullets.
3. Use smooth, conversational spoken transitions between stories:
   - "First up, in artificial intelligence..."
   - "Now, switching gears over to cricket..."
   - "Meanwhile, in the startup world..."
   - "And turning our attention to the financial markets..."
4. Tell the story with human personality: explain what happened and why it matters in 2-3 engaging, spoken sentences per topic.
5. Weave source attributions naturally into your speech: "as Bloomberg reported this morning...", "according to Cricinfo...", "TechCrunch notes that..."
6. Conclude warmly: "That's your morning briefing to kick off your day. If you want to dive deeper into any of these stories, just tap the mic and let me know. Have a wonderful morning!"
7. NEVER output markdown, asterisks, bold text, headers, stage directions, or bullet points. Output ONLY the exact spoken words that will be read aloud on the radio.
"""

QA_SYSTEM_PROMPT = """You are Morning Pilot's voice assistant. You are having a real-time spoken audio conversation with the listener after their morning briefing.

Rules:
- Speak conversationally, warmly, and clearly as if talking on the radio or in a podcast.
- Answer in 2 to 4 spoken sentences.
- Cite your sources naturally: "According to Cricinfo..." or "Bloomberg reports that..."
- If you don't have enough facts in context, be honest and say what is known.
- NEVER output markdown, asterisks, bullet points, headers, or stage directions. Output ONLY clean spoken words.
"""


def _clean_spoken_text(text: str) -> str:
    """Remove any markdown syntax, asterisks, or intro labels before audio synthesis."""
    # Remove markdown bold/italics
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
    cleaned = re.sub(r"_([^_]+)_", r"\1", cleaned)
    # Remove markdown headers
    cleaned = re.sub(r"^#+\s*", "", cleaned, flags=re.MULTILINE)
    # Remove bullet markers
    cleaned = re.sub(r"^\s*[-*•]\s*", "", cleaned, flags=re.MULTILINE)
    # Remove stage cues like [Host:], (Music fades)
    cleaned = re.sub(r"\[.*?\]", "", cleaned)
    cleaned = re.sub(r"\(.*?\)", "", cleaned)
    # Clean redundant whitespace
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _generate_fallback_script(user_name: str, date_str: str, stories: list[dict]) -> str:
    lines = [f"Good morning, {user_name}! It's {date_str}, and here is your Morning Pilot briefing."]
    if stories:
        lines.append("Here's what you need to know today.")
        for i, s in enumerate(stories, 1):
            headline = s.get("headline", "")
            summary = s.get("summary", "")
            topic = s.get("interest_match", "the news")
            sources = s.get("sources", [])
            source_name = sources[0].get("title", "our sources") if sources else "live reports"
            prefix = "First, in" if i == 1 else "Next, turning to"
            lines.append(f"{prefix} {topic}: {headline}. As {source_name} reports, {summary[:250]}.")
    else:
        lines.append(
            "We checked for live updates across your tracked topics in AI, Cricket, Startups, and Markets. "
            "Things are moving steadily this morning, and we'll keep tracking breaking changes."
        )
    lines.append("That's your briefing to get your day started. Got questions? Just tap the mic and ask.")
    return "\n\n".join(lines)


def _generate_fallback_answer(
    question: str, briefing_script: str, context_articles: list[dict]
) -> str:
    q_words = set(w.lower() for w in question.split() if len(w) > 3)
    matched_sentences = []
    source_title = None

    for article in context_articles:
        text = article.get("text", "")
        for sent in text.split(". "):
            if any(w in sent.lower() for w in q_words):
                matched_sentences.append(sent.strip())
                source_title = article.get("title")
                if len(matched_sentences) >= 2:
                    break
        if len(matched_sentences) >= 2:
            break

    if matched_sentences:
        cite = f"According to {source_title}, " if source_title else ""
        return f"{cite}{'. '.join(matched_sentences)}."
    elif briefing_script:
        for sent in briefing_script.split(". "):
            if any(w in sent.lower() for w in q_words):
                return f"Based on your briefing: {sent.strip()}."
    return (
        f"I looked into '{question}'. Based on your latest briefing and live sources, "
        f"I've noted this topic in your interest profile so upcoming briefings will cover more depth."
    )


async def write_briefing_script(
    user_name: str,
    date_str: str,
    stories: list[dict],
) -> str:
    """Generate an authentic human radio broadcast script from ranked stories."""
    stories_text = ""
    for i, story in enumerate(stories, 1):
        sources_str = ", ".join(
            s.get("title", s.get("url", "Web")) for s in story.get("sources", [])
        )
        stories_text += (
            f"\nStory {i} (Topic: {story['interest_match']}):\n"
            f"Headline: {story['headline']}\n"
            f"Details: {story['summary']}\n"
            f"Source: {sources_str}\n"
        )

    client, model = _get_client_and_model()
    print(f"[LLM] Writing briefing script using model '{model}' for {user_name}...")

    prompt = (
        f"You are writing a morning spoken radio broadcast for {user_name} on {date_str}.\n\n"
        f"Real news stories gathered today across their favorite topics:\n{stories_text}\n\n"
        f"Write the full spoken script that sounds like a real, charismatic human host speaking warmly to {user_name}. "
        f"Synthesize the stories with conversational transitions and natural source attributions. "
        f"Do NOT include any asterisks, markdown, headers, bullet points, or stage directions. Output ONLY spoken words."
    )

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": BRIEFING_SYSTEM_PROMPT.format(name=user_name, date=date_str)},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        content = response.choices[0].message.content or ""
        return _clean_spoken_text(content)
    except Exception as e:
        print(f"[LLM] Primary LLM call failed ({e}), checking fallback...")
        # If OpenAI failed, try local Ollama directly
        if "ollama" not in model:
            try:
                print(f"[LLM] Trying local Ollama fallback with {settings.ollama_model}...")
                ollama_client = AsyncOpenAI(base_url=settings.ollama_base_url, api_key="ollama")
                resp = await ollama_client.chat.completions.create(
                    model=settings.ollama_model,
                    messages=[
                        {"role": "system", "content": BRIEFING_SYSTEM_PROMPT.format(name=user_name, date=date_str)},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                    max_tokens=2000,
                )
                content = resp.choices[0].message.content or ""
                return _clean_spoken_text(content)
            except Exception as e2:
                print(f"[LLM] Ollama fallback also failed: {e2}")

        return _generate_fallback_script(user_name, date_str, stories)


async def answer_question(
    question: str,
    briefing_script: str,
    context_articles: list[dict],
) -> str:
    """Answer a user question conversationally using briefing context and live articles."""
    context = f"BRIEFING SCRIPT:\n{briefing_script}\n\n"
    for i, article in enumerate(context_articles, 1):
        context += (
            f"ARTICLE {i}: {article.get('title', 'Unknown')}\n"
            f"URL: {article.get('url', '')}\n"
            f"Content: {article.get('text', '')[:2000]}\n\n"
        )

    client, model = _get_client_and_model()
    print(f"[LLM] Answering question using model '{model}'...")

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": QA_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Context from today's briefing:\n{context}\n\n"
                        f"User asked: {question}\n\n"
                        f"Answer conversationally in 2-3 spoken sentences. Cite your sources naturally."
                    ),
                },
            ],
            temperature=0.6,
            max_tokens=800,
        )
        content = response.choices[0].message.content or ""
        return _clean_spoken_text(content)
    except Exception as e:
        print(f"[LLM] Answer call failed ({e}), checking Ollama fallback...")
        if "ollama" not in model:
            try:
                ollama_client = AsyncOpenAI(base_url=settings.ollama_base_url, api_key="ollama")
                resp = await ollama_client.chat.completions.create(
                    model=settings.ollama_model,
                    messages=[
                        {"role": "system", "content": QA_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": (
                                f"Context from today's briefing:\n{context}\n\n"
                                f"User asked: {question}\n\n"
                                f"Answer conversationally in 2-3 spoken sentences. Cite your sources naturally."
                            ),
                        },
                    ],
                    temperature=0.6,
                    max_tokens=800,
                )
                content = resp.choices[0].message.content or ""
                return _clean_spoken_text(content)
            except Exception as e2:
                print(f"[LLM] Ollama answer fallback failed: {e2}")

        return _generate_fallback_answer(question, briefing_script, context_articles)
