"""MCP tool wrappers exposed to the agent's LLM."""

from .duckduckgo_search import duckduckgo_search
from .list_inbox import list_inbox
from .read_email import read_email
from .send_email import send_email
from .reply_to_email import reply_to_email
from .draft_reply import draft_reply
from .create_calendar_event import create_calendar_event
from .load_calendar_events import load_calendar_events
from .readcv import readcv

__all__ = [
    "duckduckgo_search",
    "list_inbox",
    "read_email",
    "send_email",
    "reply_to_email",
    "draft_reply",
    "create_calendar_event",
    "load_calendar_events",
    "readcv",
]
