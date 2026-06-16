"""agent.tools.mcp_tools.reply_to_email module."""

from langchain_core.tools import tool
from core.mcp_client import call_mcp_tool

@tool
async def reply_to_email(email_id: str, body: str) -> str:
    """
    Reply to a specific email by its message ID/IMAP UID.
    Fetches the original email's subject and sender automatically to construct proper threaded replies.
    """
    return await call_mcp_tool("reply_to_email", {"email_id": email_id, "body": body})
