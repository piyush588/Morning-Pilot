"""Search and news retrieval service.

Supports:
1. TinyFish Search API (if configured)
2. GNews.io API (100 free requests/day with full summaries)
3. Direct Indian Media RSS Feeds (NDTV, The Hindu, Times of India, Indian Express)
4. Topic-specific RSS Feeds (ESPN Cricinfo for Cricket, TechCrunch for AI/Startups)
5. Google News Live RSS (India Top Stories & Topic Search)
6. DuckDuckGo HTML search fallback
"""

import html
import urllib.parse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import httpx

from app.config import settings
from app.core.cache import cache_get, cache_set

SEARCH_URL = "https://api.search.tinyfish.ai"

# Curated direct RSS feeds with rich descriptions and scrapeable direct URLs
TOPIC_RSS_FEEDS = {
    "cricket": [
        ("ESPN Cricinfo", "https://www.espncricinfo.com/rss/content/story/feeds/0.xml"),
    ],
    "ai": [
        ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
        ("TechCrunch", "https://techcrunch.com/feed/"),
    ],
    "artificial intelligence": [
        ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ],
    "startups": [
        ("TechCrunch Startups", "https://techcrunch.com/category/startups/feed/"),
    ],
    "india": [
        ("NDTV", "https://feeds.feedburner.com/ndtvnews-top-stories"),
        ("The Hindu", "https://www.thehindu.com/news/national/feeder/default.rss"),
        ("Times of India", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"),
    ],
    "national": [
        ("NDTV", "https://feeds.feedburner.com/ndtvnews-top-stories"),
        ("The Hindu", "https://www.thehindu.com/news/national/feeder/default.rss"),
    ],
}

DEFAULT_INDIA_FEEDS = [
    ("NDTV", "https://feeds.feedburner.com/ndtvnews-top-stories"),
    ("The Hindu", "https://www.thehindu.com/news/national/feeder/default.rss"),
    ("Times of India", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"),
]


def _clean_html_snippet(raw_html: str) -> str:
    """Extract plain text from an HTML snippet or description."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    # Remove script and style elements
    for s in soup(["script", "style"]):
        s.decompose()
    text = soup.get_text(separator=" ").strip()
    # Unescape HTML entities
    return html.unescape(" ".join(text.split()))


def _fetch_rss_feed(feed_url: str, default_source: str = "News", limit: int = 5) -> list[dict]:
    """Fetch and parse an RSS feed, returning structured story dicts."""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    try:
        with httpx.Client(timeout=10, headers=headers, follow_redirects=True) as client:
            resp = client.get(feed_url)
            if resp.status_code != 200:
                return []
            tree = ET.fromstring(resp.content)
            results = []
            for item in tree.findall(".//item")[:limit]:
                raw_title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                source_elem = item.find("source")
                source_name = source_elem.text if source_elem is not None and source_elem.text else default_source

                desc_raw = item.findtext("description", "")
                snippet = _clean_html_snippet(desc_raw)

                # Clean up title formatting if it contains trailing source
                title = raw_title
                if " - " in raw_title:
                    parts = raw_title.rsplit(" - ", 1)
                    title = parts[0].strip()
                    if not source_elem:
                        source_name = parts[1].strip()

                if not title:
                    continue

                results.append(
                    {
                        "title": title,
                        "url": link,
                        "source": source_name,
                        "snippet": snippet or title,
                    }
                )
            return results
    except Exception as e:
        print(f"[RSS Fetch] Failed to fetch feed {feed_url}: {e}")
        return []


def _search_gnews_api(query: str, limit: int = 5) -> list[dict]:
    """Search via GNews.io API if API key is provided (100 free requests/day)."""
    if not settings.gnews_api_key or settings.gnews_api_key.startswith("optional_"):
        return []
    try:
        url = "https://gnews.io/api/v4/search"
        params = {
            "q": query,
            "lang": "en",
            "country": "in",
            "max": limit,
            "token": settings.gnews_api_key,
        }
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for art in data.get("articles", [])[:limit]:
                    results.append(
                        {
                            "title": art.get("title", ""),
                            "url": art.get("url", ""),
                            "source": art.get("source", {}).get("name", "GNews"),
                            "snippet": art.get("description", "") or art.get("content", ""),
                        }
                    )
                if results:
                    return results
    except Exception as e:
        print(f"[GNews API] Search error: {e}")
    return []


def _search_live_web(query: str, location: str = "IN", limit: int = 5) -> list[dict]:
    """Search live web combining curated feeds, Google News RSS, and DuckDuckGo."""
    normalized_q = query.lower().strip()

    # 1. Check topic-specific curated RSS feeds first (provides rich snippets & direct URLs)
    for topic_key, feed_list in TOPIC_RSS_FEEDS.items():
        if topic_key in normalized_q:
            combined = []
            for src_name, feed_url in feed_list:
                items = _fetch_rss_feed(feed_url, default_source=src_name, limit=limit)
                combined.extend(items)
                if len(combined) >= limit:
                    break
            if combined:
                return combined[:limit]

    # 2. Check GNews API if configured
    gnews_results = _search_gnews_api(query, limit=limit)
    if gnews_results:
        return gnews_results

    # 3. Google News RSS Search
    try:
        clean_query = query.replace("latest news today", "").strip() or query
        encoded = urllib.parse.quote(clean_query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl={location}&ceid={location}:en"
        google_results = _fetch_rss_feed(url, default_source="Google News", limit=limit)
        if google_results:
            return google_results
    except Exception as e:
        print(f"[Search Fallback] Google News RSS failed: {e}")

    # 4. DuckDuckGo HTML search fallback (for rich snippets)
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
        print(f"[Search Fallback] DuckDuckGo search failed: {e}")

    # 5. Last resort: top Indian national news
    for src_name, feed_url in DEFAULT_INDIA_FEEDS:
        items = _fetch_rss_feed(feed_url, default_source=src_name, limit=limit)
        if items:
            return items[:limit]

    return []


async def search(
    query: str,
    purpose: str | None = None,
    location: str = "IN",
    language: str = "en",
    recency_minutes: int | None = 1440,
) -> list[dict]:
    """Search the web via TinyFish, GNews, curated RSS, or live search.

    Each result contains: title, url, source, snippet.
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

    # Fallback to curated feeds & live search
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
            results[topic] = topic_results[:5]
        except Exception as e:
            print(f"[Search] Failed for {topic}: {e}")
            results[topic] = []
    return results
