"""
Reply to an email using IMAP (fetch original) + SMTP (send reply).
This tool allows you to reply to a specific email by its IMAP UID.
It first fetches the original email's subject and sender using IMAP to construct proper reply headers (like In-Reply-To). 
Then it sends the reply via SMTP. Make sure to provide your email credentials in the environment variables 
    (MAIL_HOST, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_ENCRYPTION).
Example usage:
    @mcp.tool()
    async def reply_to_email(email_id: str, body: str) -> dict:
        return await reply_to_email(email_id, body)
"""

import smtplib
import imaplib
import email as email_lib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from server import mcp
from utils import credentials, ok, err, from_exception
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


def _get_original(email_id: str) -> dict | None:
    """Fetch original email subject and sender via IMAP to build proper reply headers."""
    host     = credentials.MAIL_HOST
    port     = credentials.MAIL_PORT
    use_ssl  = credentials.MAIL_ENCRYPTION

    if use_ssl:
        server = imaplib.IMAP4_SSL(host, port or 993)
    else:
        server = imaplib.IMAP4(host, port or 143)
        server.starttls()

    server.login(credentials.MAIL_USERNAME, credentials.MAIL_PASSWORD)
    server.select("inbox")

    _, data = server.fetch(email_id, "(RFC822)")
    server.close()
    server.logout()

    if not data or data[0] is None:
        return None

    msg = email_lib.message_from_bytes(data[0][1])
    return {
        "subject":    msg.get("Subject", ""),
        "from":       msg.get("From"),
        "message_id": msg.get("Message-ID"),
    }


def _build_reply(original: dict, body: str) -> MIMEMultipart:
    """Build a properly structured reply email."""
    reply = MIMEMultipart()

    # Reply subject — add Re: if not already there
    subject = original["subject"]
    reply["Subject"] = subject if subject.startswith("Re:") else f"Re: {subject}"

    # Headers
    reply["From"]       = credentials.MAIL_USERNAME
    reply["To"]         = original["from"]
    reply["In-Reply-To"] = original.get("message_id", "")
    reply["References"]  = original.get("message_id", "")

    reply.attach(MIMEText(body, "plain"))
    return reply


@mcp.tool()
async def reply_to_email(email_id: str, body: str) -> dict:
    """
    Reply to a specific email by its IMAP UID.

    Args:
        email_id: IMAP UID of the email to reply to.
        body:     The reply message body.
    """
    try:
        credentials.require("MAIL_HOST", "MAIL_USERNAME", "MAIL_PASSWORD")
        await rate_limiter.acquire("gmail")

        # Step 1 — fetch original to build proper reply headers
        original = _get_original(email_id)
        if not original:
            return err(
                message=f"Email '{email_id}' not found in inbox.",
                code="NOT_FOUND",
            )

        # Step 2 — build reply
        reply = _build_reply(original, body)

        # Step 3 — send via SMTP
        host    = credentials.MAIL_HOST
        port    = credentials.MAIL_PORT or 587
        use_ssl = credentials.MAIL_ENCRYPTION

        if use_ssl:
            smtp = smtplib.SMTP_SSL(host, 465)
        else:
            smtp = smtplib.SMTP(host, port)
            smtp.starttls()

        smtp.login(credentials.MAIL_USERNAME, credentials.MAIL_PASSWORD)
        smtp.sendmail(credentials.MAIL_USERNAME, original["from"], reply.as_string())
        smtp.quit()

        logger.info(f"Reply sent to {original['from']} for email {email_id}")
        return ok(
            data={"to": original["from"], "subject": reply["Subject"]},
            message="Reply sent successfully.",
        )

    except Exception as e:
        logger.error(f"reply_to_email failed: {e}")
        return from_exception(e)