"""
This tool generates a draft email reply based on the original email's subject and body. 
It can be used to create a response template that you can then customize and send using the send_email tool.
Example usage:
    @mcp.tool()
    async def reply_to_email(email_id: str, body: str) -> dict:
        return await reply_to_email(email_id, body)
"""
from server import mcp

@mcp.tool()
def draft_reply(original_subject: str, original_body: str, tone: str = "professional") -> str:
    """Generate a draft email reply (uses LLM internally if needed, but simple here)."""
    return f"Re: {original_subject}\n\nThank you for your message. Regarding '{original_body[:50]}...', my response is: [Your reply here]. Best regards."