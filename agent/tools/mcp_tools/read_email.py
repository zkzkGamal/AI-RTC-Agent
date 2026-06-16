"""agent.tools.mcp_tools.read_email module."""

from langchain_core.tools import tool
from core.mcp_client import call_mcp_tool

@tool
async def read_email(email_id: str) -> str:
    """
    Read the full content of a specific email by its message ID.
    Always run list_inbox first to get valid email UIDs/IDs before using this tool.
    """
    return await call_mcp_tool("read_email", {"email_id": email_id})
