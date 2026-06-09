import importlib
import pytest

duck_module = importlib.import_module("tools.search_web.duckduckgo")
from tools.search_web.duckduckgo import duckduckgo_search


@pytest.mark.asyncio
async def test_duckduckgo_search_success(monkeypatch):
    """Test successful DuckDuckGo search response mapping."""
    captured = {}

    async def fake_acquire(tool_name: str, hard_fail: bool = False):
        captured["tool_name"] = tool_name
        captured["hard_fail"] = hard_fail

    async def fake_to_thread(func, query, max_results):
        captured["func"] = func
        captured["query"] = query
        captured["max_results"] = max_results
        return [
            {
                "title": "OpenAI",
                "href": "https://openai.com",
                "body": "AI research and products.",
            },
            {
                "title": "Docs",
                "href": "https://platform.openai.com/docs",
                "body": "Developer documentation.",
            },
        ]

    monkeypatch.setattr(duck_module.rate_limiter, "acquire", fake_acquire)
    monkeypatch.setattr(duck_module.asyncio, "to_thread", fake_to_thread)

    result = await duckduckgo_search("openai", max_results=50)

    assert result["status"] == "ok"
    assert result["data"]["query"] == "openai"
    assert result["data"]["count"] == 2
    assert result["data"]["results"] == [
        {
            "title": "OpenAI",
            "url": "https://openai.com",
            "snippet": "AI research and products.",
        },
        {
            "title": "Docs",
            "url": "https://platform.openai.com/docs",
            "snippet": "Developer documentation.",
        },
    ]
    assert captured["tool_name"] == "duckduckgo"
    assert captured["max_results"] == 20
    assert captured["func"] is duck_module._search_sync


@pytest.mark.asyncio
async def test_duckduckgo_search_empty_query():
    """Test validation response for an empty query."""
    result = await duckduckgo_search("   ")

    assert result["status"] == "error"
    assert result["error"]["code"] == "VALIDATION_ERROR"
    assert result["error"]["message"] == "Query cannot be empty."
