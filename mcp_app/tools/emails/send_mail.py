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
import logging
import asyncio

from server import mcp
from service.MailService import mail_service

try:
    from mcp_app.utils import credentials, ok, err, from_exception
    from mcp_app.utils.rate_limiter import rate_limiter
except ModuleNotFoundError:
    from utils import credentials, ok, err, from_exception
    from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)
mail_service = mail_service()

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

        await asyncio.to_thread(mail_service._send_sync, subject, body, to_email)

        return ok(
            data={"to": to_email, "subject": subject},
            message="Email sent successfully.",
        )

    except Exception as e:
        logger.error(f"send_email failed: {e}")
        return from_exception(e)
