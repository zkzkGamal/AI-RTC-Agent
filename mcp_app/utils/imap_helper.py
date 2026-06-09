import imaplib
import email
from email.header import decode_header
import logging

try:
    from mcp_app.utils.auth import credentials
    from mcp_app.utils.response_parser import ok, err
except ModuleNotFoundError:
    from utils.auth import credentials
    from utils.response_parser import ok, err

logger = logging.getLogger(__name__)

def _decode_str(val):
    if not val:
        return ""
    try:
        decoded = decode_header(val)
        parts = []
        for text, encoding in decoded:
            if isinstance(text, bytes):
                parts.append(text.decode(encoding or "utf-8", errors="replace"))
            else:
                parts.append(str(text))
        return "".join(parts)
    except Exception:
        return str(val)

def list_inbox_imap(limit: int = 10) -> dict:
    try:
        credentials.require("MAIL_USERNAME", "MAIL_PASSWORD")
        username = credentials.MAIL_USERNAME
        password = credentials.MAIL_PASSWORD

        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(username, password)
        mail.select("INBOX")

        status, data = mail.search(None, "ALL")
        if status != "OK":
            return err("Failed to search inbox via IMAP.", "IMAP_ERROR")

        mail_ids = data[0].split()
        target_ids = mail_ids[-limit:]
        target_ids.reverse()

        emails = []
        for mail_id in target_ids:
            try:
                status, msg_data = mail.fetch(mail_id, "(RFC822)")
                if status != "OK":
                    continue
                for part in msg_data:
                    if isinstance(part, tuple):
                        msg = email.message_from_bytes(part[1])
                        subject = _decode_str(msg["Subject"])
                        from_ = _decode_str(msg["From"])
                        date = msg["Date"] or ""
                        
                        snippet = ""
                        if msg.is_multipart():
                            for subpart in msg.walk():
                                if subpart.get_content_type() == "text/plain":
                                    payload = subpart.get_payload(decode=True)
                                    snippet = payload.decode(errors="replace")[:150]
                                    break
                        else:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                snippet = payload.decode(errors="replace")[:150]

                        emails.append({
                            "id": mail_id.decode(),
                            "subject": subject,
                            "from": from_,
                            "date": date,
                            "snippet": snippet.strip(),
                        })
            except Exception as e:
                logger.warning(f"Failed to fetch individual mail {mail_id.decode()} via IMAP: {e}")

        mail.close()
        mail.logout()
        return ok(data={"emails": emails, "count": len(emails)})
    except Exception as e:
        logger.error(f"IMAP list_inbox failed: {e}")
        return err(f"IMAP connection failed: {e}", "IMAP_CONNECTION_ERROR")


def read_email_imap(email_id: str) -> dict:
    try:
        credentials.require("MAIL_USERNAME", "MAIL_PASSWORD")
        username = credentials.MAIL_USERNAME
        password = credentials.MAIL_PASSWORD

        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(username, password)
        mail.select("INBOX")

        status, msg_data = mail.fetch(email_id.encode(), "(RFC822)")
        if status != "OK" or not msg_data:
            mail.close()
            mail.logout()
            return err(f"Email with ID '{email_id}' not found via IMAP.", "NOT_FOUND")

        body = ""
        subject = ""
        from_ = ""
        to = ""
        date = ""
        snippet = ""

        for part in msg_data:
            if isinstance(part, tuple):
                msg = email.message_from_bytes(part[1])
                subject = _decode_str(msg["Subject"])
                from_ = _decode_str(msg["From"])
                to = _decode_str(msg["To"])
                date = msg["Date"] or ""
                
                if msg.is_multipart():
                    for subpart in msg.walk():
                        content_type = subpart.get_content_type()
                        content_disposition = str(subpart.get("Content-Disposition"))
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            payload = subpart.get_payload(decode=True)
                            body = payload.decode(errors="replace")
                            break
                    if not body:
                        for subpart in msg.walk():
                            if subpart.get_content_type() == "text/html":
                                payload = subpart.get_payload(decode=True)
                                body = payload.decode(errors="replace")
                                break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode(errors="replace")
                
                snippet = body[:150] if body else ""

        mail.close()
        mail.logout()
        return ok(data={
            "id": email_id,
            "subject": subject,
            "from": from_,
            "to": to,
            "date": date,
            "body": body,
            "snippet": snippet.strip(),
        })
    except Exception as e:
        logger.error(f"IMAP read_email failed: {e}")
        return err(f"IMAP read_email failed: {e}", "IMAP_ERROR")
