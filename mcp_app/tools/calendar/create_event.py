"""
Google Calendar MCP tool.

Creates a Google Calendar event when a valid Google OAuth token is available.
If Google Calendar is unavailable or the token does not have calendar scope,
the tool still returns a standards-compliant ICS payload as a fallback.
"""

import logging

from server import mcp
from service.CalendarICSService import calender_ics_service
from service.CalnderService import calendar_service
from service.CalendarGoogleService import google_calendar_service

try:
    from mcp_app.utils import ok, from_exception
    from mcp_app.utils.rate_limiter import rate_limiter
except ModuleNotFoundError:
    from utils import ok, from_exception
    from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

calender_ics_service = calender_ics_service()
calendar_service = calendar_service()
google_calendar_service = google_calendar_service()


@mcp.tool()
async def create_calendar_event(
    title: str,
    date: str,
    time: str,
    duration_minutes: int,
    description: str = "",
    attendees: list[str] | None = None,
) -> dict:
    """
    Create a Google Calendar event and return an ICS fallback payload.

    The Google API call is attempted first. If it fails because auth is missing,
    the token lacks Calendar scope, or the API is unavailable, the tool still
    returns a generated ICS event so the caller can import it manually.
    """
    try:
        await rate_limiter.acquire("calendar_create_event")

        start_at, end_at = calendar_service._parse_event_times(date, time, duration_minutes)
        attendees = attendees or []
        ics_string = calender_ics_service.build_ics_event(title, start_at, end_at, description, attendees)

        google_event = None
        fallback_reason = None

        try:
            google_event = await google_calendar_service.create_google_calendar_event(
                title=title,
                start_at=start_at,
                end_at=end_at,
                description=description,
                attendees=attendees,
            )
            logger.info(
                "Created Google Calendar event '%s' on %s at %s.",
                title,
                date,
                time,
            )
        except Exception as exc:
            fallback_reason = str(exc)
            logger.warning(
                "Google Calendar create failed for '%s'. Returning ICS fallback. Error: %s",
                title,
                exc,
            )

        message = (
            "Google Calendar event created successfully."
            if google_event
            else "Google Calendar unavailable; returning ICS fallback."
        )

        return ok(
            message=message,
            data={
                "provider": "google_calendar" if google_event else "ics_fallback",
                "google_event": google_event,
                "ics": ics_string,
                "fallback_reason": fallback_reason,
            },
        )
    except Exception as exc:
        logger.error("Error creating calendar event: %s", exc)
        return from_exception(exc)
