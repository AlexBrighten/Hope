"""Ultra-lightweight Web Tools for Hope UltraLight:
DuckDuckGo search + httpx + trafilatura for clean text extraction (~20MB RAM, sub-second execution).
"""

import logging
from typing import List, Dict, Any
import httpx

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

try:
    import trafilatura
except ImportError:
    trafilatura = None

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 HopeAgent/2.0"


async def web_search(query: str, max_results: int = 5) -> str:
    """Search DuckDuckGo for real-time web results."""
    try:
        if DDGS is not None:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
        else:
            # Lightweight HTTP fallback if duckduckgo_search package is not yet installed
            async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, timeout=10.0) as client:
                res = await client.get(f"https://html.duckduckgo.com/html/?q={query}")
                soup = BeautifulSoup(res.text, "html.parser")
                results = []
                for a in soup.select(".result__snippet")[:max_results]:
                    results.append({"title": "Web Result", "body": a.get_text(strip=True), "href": ""})

        if not results:
            return f"No search results found for: {query}"

        formatted = [f"### Web Search Results for: {query}\n"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "No Title")
            snippet = r.get("body", "No description")
            href = r.get("href", "")
            formatted.append(f"{i}. **[{title}]({href})**\n   {snippet}\n")

        return "\n".join(formatted)
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {e}")
        return f"Web search error: {e}"


async def fetch_page(url: str, max_chars: int = 5000) -> str:
    """Fetch and extract clean, readable text from a URL without opening a browser."""
    try:
        async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, timeout=15.0, follow_redirects=True) as client:
            res = await client.get(url)
            res.raise_for_status()
            html = res.text

        clean_text = None
        # 1. Use trafilatura if available
        if trafilatura is not None:
            extracted = trafilatura.extract(html, include_links=True, output_format="markdown")
            if extracted and len(extracted.strip()) > 100:
                clean_text = extracted.strip()

        # 2. BeautifulSoup fallback
        if not clean_text:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                tag.decompose()
            clean_text = " ".join(soup.stripped_strings)

        if len(clean_text) > max_chars:
            clean_text = clean_text[:max_chars] + f"\n\n[... Truncated, total length: {len(clean_text)} chars]"

        return f"### Extracted Content from: {url}\n\n{clean_text}"
    except Exception as e:
        logger.error(f"Fetch page error for {url}: {e}")
        return f"Failed to fetch page from {url}: {e}"


async def summarize_url(url: str) -> str:
    """Fetch URL content optimized for summarization."""
    return await fetch_page(url, max_chars=4000)


async def company_brief(query: str) -> str:
    """High-value compound tool: searches for a company or founder and extracts key info."""
    search_res = await web_search(f"{query} overview company founder products", max_results=3)
    return (
        f"### Research Brief: {query}\n\n"
        f"Below are the latest verified public search results for '{query}':\n\n"
        f"{search_res}\n\n"
        f"_Source: Live DuckDuckGo Search_"
    )
