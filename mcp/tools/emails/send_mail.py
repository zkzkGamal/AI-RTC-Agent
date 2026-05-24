"""
Send emails via SMTP using credentials from utils.
Make sure to set the following environment variables in your .env file:
    MAIL_HOST: SMTP server host (e.g., smtp.gmail.com)
    MAIL_PORT: SMTP server port (e.g., 587 for TLS, 465 for SSL)
    MAIL_USERNAME: Your email address (e.g., your Gmail address)
    MAIL_PASSWORD: Your email password or app-specific password
    MAIL_ENCRYPTION: "true" for SSL, "false" for TLS
Example usage:
    @mcp.tool()
    async def send_welcome_email(user_email: str) -> dict:
        subject = "Welcome to Our Service!"
        body = "Thank you for signing up. We're excited to have you on board!"
        return await send_email(subject, body, [user_email])
"""
import smtplib
import logging
import asyncio
from email.message import EmailMessage
from typing import List

from server import mcp
from utils import credentials, ok, err, from_exception
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


def _send_sync(subject: str, body: str, to_email: List[str]) -> None:
    """
    Internal sync SMTP sender — runs in a thread via asyncio.to_thread.
    Raises on failure so from_exception() can catch it.
    """
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"]    = f"{credentials.MAIL_USERNAME}"
    msg["To"]      = ", ".join(to_email)
    msg.set_content(body)

    host    = credentials.MAIL_HOST
    port    = credentials.MAIL_PORT or 587
    use_ssl = credentials.MAIL_ENCRYPTION

    if use_ssl:
        with smtplib.SMTP_SSL(host, 465, timeout=10) as server:
            server.login(credentials.MAIL_USERNAME, credentials.MAIL_PASSWORD)
            logger.info("SMTP SSL login successful.")
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(credentials.MAIL_USERNAME, credentials.MAIL_PASSWORD)
            logger.info("SMTP TLS login successful.")
            server.send_message(msg)

    logger.info(f"Email sent to {to_email}")


@mcp.tool()
async def send_email(subject: str, body: str, to_email: list[str]) -> dict:
    """
    Send an email via SMTP.

    Args:
        subject:  Email subject.
        body:     Email body.
        to_email: List of recipient email addresses.

    Returns:
        ok() on success, err() on failure.
    """
    try:
        if not to_email:
            return err(message="No recipients provided.", code="VALIDATION_ERROR")

        credentials.require("MAIL_HOST", "MAIL_USERNAME", "MAIL_PASSWORD")
        await rate_limiter.acquire("gmail")

        await asyncio.to_thread(_send_sync, subject, body, to_email)

        return ok(
            data={"to": to_email, "subject": subject},
            message="Email sent successfully.",
        )

    except Exception as e:
        logger.error(f"send_email failed: {e}")
        return from_exception(e)