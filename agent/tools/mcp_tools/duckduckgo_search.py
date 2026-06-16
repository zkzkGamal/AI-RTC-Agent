"""agent.tools.mcp_tools.duckduckgo_search module."""

from langchain_core.tools import tool
from core.mcp_client import call_mcp_tool

@tool
async def duckduckgo_search(query: str, max_results: int = 2) -> str:
    """
    Search the web using DuckDuckGo. 
    Use this tool when the user asks for current events, news, or general web search queries.
    """
    capped_results = min(max_results, 2)
    return await call_mcp_tool("duckduckgo_search", {"query": query, "max_results": capped_results})
