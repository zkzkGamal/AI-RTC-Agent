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

try:
    from mcp_app.utils import ok, from_exception
    from mcp_app.utils.rate_limiter import rate_limiter
except ModuleNotFoundError:
    from utils import ok, from_exception
    from utils.rate_limiter import rate_limiter
from service.create_header import _headers

from pathlib import Path
logger = logging.getLogger(__name__)
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

GMAIL_API = os.getenv("GMAIL_API_URL", "https://gmail.googleapis.com/gmail/v1/users/me")


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
            res = await client.get(
                f"{GMAIL_API}/messages",
                headers=_headers(),
                params={"maxResults": limit, "labelIds": "INBOX"},
            )
            res.raise_for_status()
            messages = res.json().get("messages", [])

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
        logger.warning(f"Gmail API list_inbox failed: {e}. Attempting IMAP fallback...")
        try:
            try:
                from mcp_app.utils.imap_helper import list_inbox_imap
            except ModuleNotFoundError:
                from utils.imap_helper import list_inbox_imap
            return list_inbox_imap(limit)
        except Exception as imap_err:
            logger.error(f"IMAP fallback failed: {imap_err}")
            return from_exception(e)
