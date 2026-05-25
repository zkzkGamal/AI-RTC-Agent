"""Top-level MCP tool exports."""

from .stt.stt import stt
from .emails import (
    check_inbox,
    list_inbox,
    draft_reply,
    send_email,
    read_email,
    reply_to_email,
)
from .search_web import duckduckgo_search, search_web
from .calendar import create_calendar_event, load_calendar_events

__all__ = [
    "stt",
    "check_inbox",
    "list_inbox",
    "draft_reply",
    "send_email",
    "read_email",
    "reply_to_email",
    "duckduckgo_search",
    "search_web",
    "create_calendar_event",
    "load_calendar_events",
]
