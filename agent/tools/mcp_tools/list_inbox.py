from langchain_core.tools import tool
from core.mcp_client import call_mcp_tool

@tool
async def list_inbox(limit: int = 10) -> str:
    """
    List recent emails from Gmail inbox.
    Useful to check for new messages, get sender information, subject lines, and email IDs.
    """
    return await call_mcp_tool("list_inbox", {"limit": limit})
