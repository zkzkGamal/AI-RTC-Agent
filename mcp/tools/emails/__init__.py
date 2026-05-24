"""
This module contains tools for email management, including checking the inbox, drafting replies, sending emails, reading emails, and replying to emails.

Tools:
- check_inbox: Check the user's email inbox for new messages.
- draft_reply: Draft a reply to a specific email.
- send_email: Send an email to a specified recipient.
- read_email: Read the content of a specific email.
- reply_to_email: Reply to a specific email with a drafted message.
"""
from .check_inbox import check_inbox
from .draft import draft_reply
from .send_mail import send_email
from .read_email import read_email
from .reply_to_email import reply_to_email
