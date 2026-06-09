"""
Email tool exports.

`check_inbox.py` currently defines the inbox tool as `list_inbox`, so we
re-export it under both names to keep imports stable while the API settles.
"""

from .check_inbox import list_inbox
from .draft import draft_reply
from .send_mail import send_email
from .read_email import read_email
from .reply_to_email import reply_to_email

# Backward-compatible alias for older imports.
check_inbox = list_inbox

__all__ = [
    "check_inbox",
    "list_inbox",
    "draft_reply",
    "send_email",
    "read_email",
    "reply_to_email",
]
