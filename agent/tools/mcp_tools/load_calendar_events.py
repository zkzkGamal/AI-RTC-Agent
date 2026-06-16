"""agent.tools.mcp_tools.load_calendar_events module."""

from langchain_core.tools import tool
from core.mcp_client import call_mcp_tool

@tool
async def load_calendar_events(
    scope: str = "today",
    ics_content: str = "",
    include_google: bool = True,
) -> str:
    """
    Load calendar events from Google Calendar or optional raw iCalendar (.ics) content.
    - scope: 'today' for today's events, or 'all' for all events.
    - ics_content: optional raw ICS content to parse and merge into the results.
    - include_google: true to fetch from Google Calendar, false to only parse ics_content.
    """
    return await call_mcp_tool(
        "load_calendar_events",
        {"scope": scope, "ics_content": ics_content, "include_google": include_google},
    )
