from langchain_core.tools import tool
from core.mcp_client import call_mcp_tool

@tool
async def create_calendar_event(
    title: str,
    date: str,
    time: str,
    duration_minutes: int,
    description: str = "",
    attendees: list[str] = None,
) -> str:
    """
    Create a new calendar event on Google Calendar.
    - date must be in YYYY-MM-DD format.
    - time must be in HH:MM (24-hour) format.
    - duration_minutes must be greater than 0.
    Falls back to building and returning a standard iCalendar (.ics) string if Google Calendar is unavailable.
    """
    args = {
        "title": title,
        "date": date,
        "time": time,
        "duration_minutes": duration_minutes,
        "description": description,
    }
    if attendees is not None:
        args["attendees"] = attendees
    return await call_mcp_tool("create_calendar_event", args)
