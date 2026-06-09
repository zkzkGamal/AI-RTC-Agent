from langchain_core.tools import tool
from core.mcp_client import call_mcp_tool

@tool
async def draft_reply(original_subject: str, original_body: str, tone: str = "professional") -> str:
    """
    Generate a draft email reply based on the original email's subject and body.
    Allows for customization of the response tone (e.g. professional, casual).
    """
    return await call_mcp_tool("draft_reply", {"original_subject": original_subject, "original_body": original_body, "tone": tone})
