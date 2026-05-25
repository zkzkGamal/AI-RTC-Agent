"""
Google Calendar + ICS event loader for MCP.

Loads Google Calendar events and can also parse ICS content supplied by the caller.
Supports filtering to today's events or returning all available events.
"""

import logging
from server import mcp

try:
    from mcp.utils import ok, from_exception
    from mcp.utils.rate_limiter import rate_limiter
except ModuleNotFoundError:
    from utils import ok, from_exception
    from utils.rate_limiter import rate_limiter
    
from service.CalnderService import calendar_service
from service.CalendarICSService import calender_ics_service
from service.CalendarGoogleService import google_calendar_service

calendar_service = calendar_service()
calender_ics_service = calender_ics_service()
google_calendar_service = google_calendar_service()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@mcp.tool()
async def load_calendar_events(
    scope: str = "today",
    ics_content: str = "",
    include_google: bool = True,
) -> dict:
    """
    Load calendar events from Google Calendar and optional ICS content.

    Args:
        scope: 'today' for today's events only, or 'all' for all available events.
        ics_content: Optional raw ICS text to parse and merge into results.
        include_google: Whether to fetch events from Google Calendar.
    """
    try:
        await rate_limiter.acquire("calendar")

        google_events = []
        ics_events = []
        google_error = None

        if include_google:
            try:
                google_events = await google_calendar_service.load_google_calendar_events(scope=scope)
            except Exception as exc:
                google_error = str(exc)
                logger.warning("Google Calendar load failed. Continuing with ICS only. Error: %s", exc)

        if ics_content.strip():
            ics_events = calender_ics_service.load_ics_events(ics_content, scope=scope)

        events = sorted(
            google_events + ics_events,
            key=lambda item: item.get("start_at") or "",
        )

        message = (
            "Calendar events loaded successfully."
            if not google_error
            else "Google Calendar unavailable; returning available ICS events only."
        )

        return ok(
            message=message,
            data={
                "scope": scope,
                "events": events,
                "count": len(events),
                "sources": {
                    "google_calendar": len(google_events),
                    "ics": len(ics_events),
                },
                "google_error": google_error,
            },
        )
    except Exception as exc:
        logger.error("Error loading calendar events: %s", exc)
        return from_exception(exc)
