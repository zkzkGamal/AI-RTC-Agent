"""
Read emails using Gmail OAuth token — no IMAP, no password.
This tool fetches the full content of a specific email by its Gmail message ID, 
which you can get from the list_inbox tool. It uses the Gmail API and requires a valid OAuth token (see get_token.py)
with "https://www.googleapis.com/auth/gmail.modify" scope.
Usage:
    # First, list recent emails to get their IDs
    emails = await list_inbox(limit=5)
    print(emails)
"""

import logging ,os
import httpx
from dotenv import load_dotenv

from server import mcp
from utils import credentials, ok, err, from_exception
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)
load_dotenv()

GMAIL_API = os.getenv("GMAIL_API_URL", "https://gmail.googleapis.com/gmail/v1/users/me")

def _headers() -> dict:
    """Load fresh token and return auth headers."""
    token = credentials.load_gmail_token()
    return {"Authorization": f"Bearer {token}"}


@mcp.tool()
async def list_inbox(limit: int = 10) -> dict:
    """
    List recent emails from Gmail inbox.

    Args:
        limit: Number of recent emails to return (default 10, max 50).
    """
    try:
        await rate_limiter.acquire("gmail")
        limit = min(limit, 50)

        async with httpx.AsyncClient() as client:
            # Step 1 — get list of message IDs
            res = await client.get(
                f"{GMAIL_API}/messages",
                headers=_headers(),
                params={"maxResults": limit, "labelIds": "INBOX"},
            )
            res.raise_for_status()
            messages = res.json().get("messages", [])

            # Step 2 — fetch metadata for each
            emails = []
            for msg in messages:
                detail = await client.get(
                    f"{GMAIL_API}/messages/{msg['id']}",
                    headers=_headers(),
                    params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
                )
                detail.raise_for_status()
                data    = detail.json()
                headers = {h["name"]: h["value"] for h in data["payload"]["headers"]}
                emails.append({
                    "id":      data["id"],
                    "subject": headers.get("Subject", "(no subject)"),
                    "from":    headers.get("From"),
                    "date":    headers.get("Date"),
                    "snippet": data.get("snippet", ""),
                })

        return ok(data={"emails": emails, "count": len(emails)})

    except Exception as e:
        logger.error(f"list_inbox failed: {e}")
        return from_exception(e)