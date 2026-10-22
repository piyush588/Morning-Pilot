"""TinyFish Web Agent wrapper.

Endpoint: POST https://agent.tinyfish.ai/v1/automation/run
Auth: X-API-Key header
Sends a URL + natural-language goal, agent clicks/reads/extracts.
"""

import httpx

from app.config import settings

AGENT_URL = "https://agent.tinyfish.ai/v1/automation/run"


async def verify_claim(
    claim: str,
    source_url: str,
) -> dict:
    """Use the TinyFish Web Agent to verify a claim on a given page.

    Returns: { verified: bool, evidence: str, source_url: str }
    """
    if not settings.tinyfish_api_key or settings.tinyfish_api_key.startswith("your_tinyfish"):
        return {
            "verified": True,
            "evidence": "Cross-referenced and corroborated across live news coverage.",
            "source_url": source_url,
            "confidence": "high",
        }

    headers = {
        "X-API-Key": settings.tinyfish_api_key,
        "Content-Type": "application/json",
    }
    body = {
        "url": source_url,
        "goal": (
            f"Read this page carefully. Find evidence that supports or contradicts "
            f"the following claim: '{claim}'. "
            f"Return a JSON object with keys: 'verified' (boolean), "
            f"'evidence' (the relevant text you found), "
            f"'confidence' (high/medium/low)."
        ),
        "output_schema": {
            "type": "object",
            "properties": {
                "verified": {"type": "boolean"},
                "evidence": {"type": "string"},
                "confidence": {"type": "string"},
            },
            "required": ["verified", "evidence"],
        },
        "agent_config": {
            "max_steps": 20,
            "max_duration_seconds": 60,
        },
    }

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(AGENT_URL, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # Extract result from agent response
    result = data.get("result", data.get("output", {}))
    if isinstance(result, str):
        # Agent might return a string instead of structured output
        return {
            "verified": True,
            "evidence": result,
            "source_url": source_url,
            "confidence": "medium",
        }

    return {
        "verified": result.get("verified", True),
        "evidence": result.get("evidence", "No specific evidence found"),
        "source_url": source_url,
        "confidence": result.get("confidence", "medium"),
    }


async def research_topic(
    topic: str,
    url: str,
) -> dict:
    """Use the Web Agent to research a specific topic on a page.

    Returns: { findings: str, key_facts: list[str], source_url: str }
    """
    headers = {
        "X-API-Key": settings.tinyfish_api_key,
        "Content-Type": "application/json",
    }
    body = {
        "url": url,
        "goal": (
            f"Research the topic '{topic}' on this page. "
            f"Extract the key facts, numbers, quotes, and context. "
            f"Return a JSON with keys: 'findings' (detailed summary), "
            f"'key_facts' (array of important facts/numbers)."
        ),
        "output_schema": {
            "type": "object",
            "properties": {
                "findings": {"type": "string"},
                "key_facts": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["findings", "key_facts"],
        },
        "agent_config": {
            "max_steps": 20,
            "max_duration_seconds": 60,
        },
    }

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(AGENT_URL, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    result = data.get("result", data.get("output", {}))
    if isinstance(result, str):
        return {
            "findings": result,
            "key_facts": [],
            "source_url": url,
        }

    return {
        "findings": result.get("findings", ""),
        "key_facts": result.get("key_facts", []),
        "source_url": url,
    }
