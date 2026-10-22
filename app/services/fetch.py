"""TinyFish Fetch API wrapper.

Endpoint: POST https://api.fetch.tinyfish.ai
Auth: X-API-Key header
Renders URLs in a real browser and returns clean markdown/text.
"""

import httpx

from app.config import settings
from app.core.cache import cache_get, cache_set

FETCH_URL = "https://api.fetch.tinyfish.ai"


async def fetch_urls(
    urls: list[str],
    purpose: str | None = None,
    fmt: str = "markdown",
) -> list[dict]:
    """Fetch and extract clean content from one or more URLs.

    Returns a list of dicts with: url, title, text, error (if any).
    Max 10 URLs per batch (TinyFish limit).
    """
    # Check cache for each URL
    uncached_urls = []
    cached_results = []
    for url in urls:
        cache_key = f"fetch:{url}"
        cached = cache_get(cache_key)
        if cached is not None:
            cached_results.append(cached)
        else:
            uncached_urls.append(url)

    if not uncached_urls:
        return cached_results

    # If TinyFish API key is valid, try TinyFish first
    if settings.tinyfish_api_key and not settings.tinyfish_api_key.startswith("your_tinyfish"):
        try:
            headers = {
                "X-API-Key": settings.tinyfish_api_key,
                "Content-Type": "application/json",
            }
            body = {
                "urls": uncached_urls[:10],  # Max 10 per batch
                "format": fmt,
                "links": False,
            }
            if purpose:
                body["purpose"] = purpose

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(FETCH_URL, json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            fetched = []
            for page in data.get("results", []):
                result = {
                    "url": page.get("url", ""),
                    "title": page.get("title", ""),
                    "text": page.get("text", page.get("content", "")),
                }
                cache_set(f"fetch:{result['url']}", result)
                fetched.append(result)

            for error in data.get("errors", []):
                fetched.append(
                    {
                        "url": error.get("url", ""),
                        "title": "",
                        "text": "",
                        "error": error.get("error", "Unknown fetch error"),
                    }
                )

            if fetched:
                return cached_results + fetched
        except Exception as e:
            print(f"[Fetch] TinyFish fetch failed ({e}), falling back to direct web fetch")

    # Fallback: direct HTTP fetch and clean HTML extraction
    from bs4 import BeautifulSoup

    fetched = []
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
        for url in uncached_urls[:10]:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title = soup.title.string.strip() if soup.title and soup.title.string else ""
                    
                    # Extract article paragraphs
                    paras = [
                        p.get_text().strip()
                        for p in soup.find_all("p")
                        if len(p.get_text().strip()) > 35
                    ]
                    text = "\n\n".join(paras[:8])
                    
                    result = {
                        "url": str(resp.url),
                        "title": title,
                        "text": text,
                    }
                    cache_set(f"fetch:{url}", result)
                    fetched.append(result)
                else:
                    fetched.append({"url": url, "title": "", "text": "", "error": f"HTTP {resp.status_code}"})
            except Exception as e:
                fetched.append({"url": url, "title": "", "text": "", "error": str(e)})

    return cached_results + fetched


async def fetch_article(url: str, purpose: str | None = None) -> dict:
    """Convenience: fetch a single URL and return its content dict."""
    results = await fetch_urls([url], purpose=purpose)
    return results[0] if results else {"url": url, "title": "", "text": "", "error": "No result"}
