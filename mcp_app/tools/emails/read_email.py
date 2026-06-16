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

import logging , os
import httpx
from dotenv import load_dotenv

from server import mcp

try:
    from mcp_app.utils import ok, err, from_exception
    from mcp_app.utils.rate_limiter import rate_limiter
except ModuleNotFoundError:
    from utils import ok, err, from_exception
    from utils.rate_limiter import rate_limiter
from service.create_header import _headers

from pathlib import Path
logger = logging.getLogger(__name__)
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

GMAIL_API = os.getenv("GMAIL_API_URL", "https://gmail.googleapis.com/gmail/v1/users/me")


@mcp.tool()
async def read_email(email_id: str) -> dict:
    """
    Read a specific email full content by its Gmail message ID.

    Args:
        email_id: Gmail message ID (get it from list_inbox).
    """
    try:
        await rate_limiter.acquire("gmail")

        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{GMAIL_API}/messages/{email_id}",
                headers=_headers(),
                params={"format": "full"},
            )

            if res.status_code == 404:
                return err(message=f"Email '{email_id}' not found.", code="NOT_FOUND")

            res.raise_for_status()
            data    = res.json()
            headers = {h["name"]: h["value"] for h in data["payload"]["headers"]}

            body = ""
            parts = data["payload"].get("parts", [])
            if parts:
                for part in parts:
                    if part["mimeType"] == "text/plain":
                        import base64
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode(errors="replace")
                        break
            else:
                import base64
                raw = data["payload"]["body"].get("data", "")
                body = base64.urlsafe_b64decode(raw).decode(errors="replace") if raw else ""

        return ok(data={
            "id":      data["id"],
            "subject": headers.get("Subject", "(no subject)"),
            "from":    headers.get("From"),
            "to":      headers.get("To"),
            "date":    headers.get("Date"),
            "body":    body,
            "snippet": data.get("snippet", ""),
        })

    except Exception as e:
        logger.warning(f"Gmail API read_email failed: {e}. Attempting IMAP fallback...")
        try:
            try:
                from mcp_app.utils.imap_helper import read_email_imap
            except ModuleNotFoundError:
                from utils.imap_helper import read_email_imap
            return read_email_imap(email_id)
        except Exception as imap_err:
            logger.error(f"IMAP fallback failed: {imap_err}")
            return from_exception(e)
