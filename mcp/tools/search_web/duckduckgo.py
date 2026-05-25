"""
This tool performs a DuckDuckGo search and returns a list of results with title, link, and snippet.
It uses the ddgs Python library to query DuckDuckGo. Make sure to install it via pip install ddgs.
Make sure to set any necessary credentials or API keys in the environment variables if required (though DuckDuckGo search typically doesn't require auth).
Example usage:
    @mcp.tool()
    async def search_web(query: str) -> list:
        return await duckduckgo_search(query)
"""
"""
tools/search_web/duckduckgo.py
───────────────────────────────
DuckDuckGo search — no API key required.
"""

import logging
import asyncio
from duckduckgo_search import DDGS

from server import mcp

try:
    from mcp.utils import ok, err, from_exception
    from mcp.utils.rate_limiter import rate_limiter
except ModuleNotFoundError:
    from utils import ok, err, from_exception
    from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


def _search_sync(query: str, max_results: int) -> list:
    """Sync DDG search — runs in a thread via asyncio.to_thread."""
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results))


@mcp.tool()
async def duckduckgo_search(query: str, max_results: int = 5) -> dict:
    """
    Search the web using DuckDuckGo. No API key required.

    Args:
        query:       Search query string.
        max_results: Number of results to return (default 5, max 20).

    Returns:
        List of results with title, url, and snippet.
    """
    try:
        if not query.strip():
            return err(message="Query cannot be empty.", code="VALIDATION_ERROR")

        max_results = min(max_results, 20)
        await rate_limiter.acquire("duckduckgo")

        raw = await asyncio.to_thread(_search_sync, query, max_results)

        results = [
            {
                "title":   r.get("title", ""),
                "url":     r.get("href", ""),
                "snippet": r.get("body", ""),
            }
            for r in raw
        ]

        logger.info(f"DuckDuckGo: {len(results)} results for '{query}'")
        return ok(data={"query": query, "results": results, "count": len(results)})

    except Exception as e:
        logger.error(f"duckduckgo_search failed: {e}")
        return from_exception(e)
