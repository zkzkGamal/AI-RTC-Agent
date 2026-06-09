"""
MailService: A simple email sending service using SMTP.
Provides two main functions:
1. send_email(subject, body, to_email): Send a new email to specified recipients.
2. reply_to_email(email_id, body): Reply to an existing email by its IMAP UID, automatically fetching original email details to construct proper reply headers.
"""

import smtplib , imaplib
import logging
import email as email_lib
from email.message import EmailMessage
from typing import List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from mcp_app.utils import credentials
except ModuleNotFoundError:
    from utils import credentials


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class mail_service:
    """A simple email sending service using SMTP and IMAP for fetching original emails when replying."""
    def __init__(self):
        """
            How to use:
            1. Ensure MAIL_HOST, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, and MAIL_ENCRYPTION are set in credentials.
            2. Call send_email(subject, body, to_email) from your tools to send emails.
            3. Call reply_to_email(email_id, body) to reply to existing emails, which will fetch original email details and construct proper reply headers.
        """
        pass
    
    def _send_sync(
        self , 
        subject: str, 
        body: str,
        to_email: List[str]
    ) -> None:
        """
            Internal sync SMTP sender — runs in a thread via asyncio.to_thread.
            Raises on failure so from_exception() can catch it.
        """
        try:
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
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise ValueError(f"Could not send email to {to_email} due to: {e}")
        
    def _get_original(
        self ,
        email_id: str
    ) -> dict | None:
        """Fetch original email subject and sender via IMAP to build proper reply headers."""
        try:
            host    = credentials.MAIL_HOST
            port    = credentials.MAIL_PORT or 993
            use_ssl = credentials.MAIL_ENCRYPTION

            if use_ssl:
                mail = imaplib.IMAP4_SSL(host, port)
            else:
                mail = imaplib.IMAP4(host, port)

            mail.login(credentials.MAIL_USERNAME, credentials.MAIL_PASSWORD)
            mail.select("inbox")

            result, data = mail.uid("fetch", email_id, "(RFC822)")
            if result != "OK":
                logger.error(f"IMAP fetch failed for email ID {email_id}: {result}")
                return None

            raw_email = data[0][1]
            email_message = email_lib.message_from_bytes(raw_email)

            original = {
                "from": email_message["From"],
                "subject": email_message["Subject"],
                "message_id": email_message["Message-ID"],
            }
            mail.logout()
            return original
        except Exception as e:
            logger.error(f"Failed to fetch original email: {e}")
            raise ValueError(f"Could not fetch original email with ID {email_id}")
        
    def _build_reply(
        self ,
        original: dict, 
        body: str
    ) -> MIMEMultipart:
        """Build a properly structured reply email."""
        try:
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
        except Exception as e:
            logger.error(f"Failed to build reply: {e}")
            raise ValueError("Could not build reply email due to invalid original email data.")



