"""TinyFish Search API wrapper.

Endpoint: GET https://api.search.tinyfish.ai
Auth: X-API-Key header
"""

import httpx

from app.config import settings
from app.core.cache import cache_get, cache_set

import html
import urllib.parse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

SEARCH_URL = "https://api.search.tinyfish.ai"


def _search_live_web(query: str, location: str = "IN", limit: int = 5) -> list[dict]:
    """Fallback search using Google News RSS and clean parsing for live breaking news."""
    try:
        clean_query = query.replace("latest news today", "").strip() or query
        encoded = urllib.parse.quote(clean_query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl={location}&ceid={location}:en"
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        
        with httpx.Client(timeout=10, headers=headers) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                tree = ET.fromstring(resp.content)
                results = []
                for item in tree.findall(".//item")[:limit]:
                    raw_title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    source_elem = item.find("source")
                    source_name = source_elem.text if source_elem is not None else "News Source"
                    
                    desc_raw = item.findtext("description", "")
                    soup = BeautifulSoup(desc_raw, "html.parser")
                    snippet = soup.get_text(separator=" ").strip() or raw_title
                    
                    # Clean up Google title format "Headline - Source"
                    title = raw_title
                    if " - " in raw_title:
                        title = raw_title.rsplit(" - ", 1)[0].strip()

                    results.append(
                        {
                            "title": title,
                            "url": link,
                            "source": source_name,
                            "snippet": snippet,
                        }
                    )
                if results:
                    return results
    except Exception as e:
        print(f"[Search Fallback] RSS search failed: {e}")

    # Fallback 2: DuckDuckGo HTML search
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        with httpx.Client(timeout=10, headers=headers) as client:
            r = client.post("https://html.duckduckgo.com/html/", data={"q": query})
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                ddg_results = []
                for el in soup.select(".result")[:limit]:
                    t_el = el.select_one(".result__title a")
                    s_el = el.select_one(".result__snippet")
                    if t_el and s_el:
                        ddg_results.append(
                            {
                                "title": t_el.get_text().strip(),
                                "url": t_el.get("href", ""),
                                "source": "Web",
                                "snippet": s_el.get_text().strip(),
                            }
                        )
                if ddg_results:
                    return ddg_results
    except Exception as e:
        print(f"[Search Fallback] DDG search failed: {e}")

    return []


async def search(
    query: str,
    purpose: str | None = None,
    location: str = "IN",
    language: str = "en",
    recency_minutes: int | None = 1440,  # last 24 hours by default
) -> list[dict]:
    """Search the web via TinyFish or live fallback and return a list of result dicts.

    Each result contains: title, url, snippet.
    """
    cache_key = f"search:{query}:{recency_minutes}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    # If TinyFish API key is valid, try TinyFish first
    if settings.tinyfish_api_key and not settings.tinyfish_api_key.startswith("your_tinyfish"):
        try:
            params = {
                "query": query,
                "location": location,
                "language": language,
            }
            if purpose:
                params["purpose"] = purpose
            if recency_minutes:
                params["recency_minutes"] = recency_minutes

            headers = {
                "X-API-Key": settings.tinyfish_api_key,
            }

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(SEARCH_URL, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            results = data.get("results", data.get("organic_results", []))
            normalized = []
            for r in results:
                normalized.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", r.get("link", "")),
                        "source": r.get("source", "Web"),
                        "snippet": r.get("snippet", r.get("description", "")),
                    }
                )
            if normalized:
                cache_set(cache_key, normalized)
                return normalized
        except Exception as e:
            print(f"[Search] TinyFish API call failed ({e}), falling back to live web search")

    # Fallback to live search
    live_results = _search_live_web(query, location=location, limit=5)
    if live_results:
        cache_set(cache_key, live_results)
        return live_results

    return []


async def search_for_interests(interests: list[dict]) -> dict[str, list[dict]]:
    """Search for multiple interests in parallel.

    Returns {topic: [results]} mapping.
    """
    results = {}
    for interest in interests:
        topic = interest["topic"]
        query = f"{topic} latest news today"
        purpose = f"Finding today's top news about {topic} for a morning briefing"
        try:
            topic_results = await search(query=query, purpose=purpose)
            results[topic] = topic_results[:5]  # Top 5 per interest
        except Exception as e:
            print(f"[Search] Failed for {topic}: {e}")
            results[topic] = []
    return results
