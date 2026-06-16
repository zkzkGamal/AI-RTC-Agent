"""agent.tools.mcp_tools.send_email module."""

from langchain_core.tools import tool
from core.mcp_client import call_mcp_tool

@tool
async def send_email(subject: str, body: str, to_email: list[str]) -> str:
    """
    Send an email via SMTP.
    Requires subject, body, and a list of recipient email addresses.
    """
    return await call_mcp_tool("send_email", {"subject": subject, "body": body, "to_email": to_email})
