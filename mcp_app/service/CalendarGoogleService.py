"""
Service for interacting with Google Calendar API.
This service provides methods to create events and load events from Google Calendar.
It is used in calendar tools to manage events and as a primary source of calendar data.
The GOOGLE_CALENDAR_API_URL environment variable can be set to specify the API endpoint,
defaulting to the primary calendar events endpoint.
"""

from service.create_header import _headers
from service.CalnderService import calendar_service

import httpx , os , logging
from dotenv import load_dotenv
from datetime import datetime


from pathlib import Path
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
calendar_service = calendar_service()

class google_calendar_service:
    """ Service for interacting with Google Calendar API.
    Provides methods to create events and load events from Google Calendar.
    It is used in calendar tools to manage events and as a primary source of calendar data.
    The GOOGLE_CALENDAR_API_URL environment variable can be set to specify the API endpoint,
    defaulting to the primary calendar events endpoint.
    Usage:
        1. Ensure you have a valid OAuth token with Calendar scope set in the environment.
        2. Set the GOOGLE_CALENDAR_API_URL environment variable if you want to use a custom calendar or endpoint.
        3. Call create_google_calendar_event to create events or load_google_calendar_events to fetch events.
        4. Handle exceptions gracefully, as API calls may fail due to auth issues or service unavailability. The tools using this service will fallback to ICS generation if needed and log any errors encountered.
    """
    def __init__(self):
        """
        How to use:
        1. Ensure you have a valid OAuth token with Calendar scope set in the environment.
        2. Set the GOOGLE_CALENDAR_API_URL environment variable if you want to use a custom calendar or endpoint.
        3. Call create_google_calendar_event to create events or load_google_calendar_events to fetch events.
        4. Handle exceptions gracefully, as API calls may fail due to auth issues or service unavailability. 
        The tools using this service will fallback to ICS generation if needed and log any errors encountered.
        args:
            title: The event title/summary.
            start_at: The event start time as a datetime object.
            end_at: The event end time as a datetime object.
            description: Optional event description.
            attendees: Optional list of attendee email addresses.
        """
        self.GOOGLE_CALENDAR_API = os.getenv(
            "GOOGLE_CALENDAR_API_URL",
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        )

    async def create_google_calendar_event(
        self,
        title: str,
        start_at: datetime,
        end_at: datetime,
        description: str = "",
        attendees: list[str] | None = None,
    ) -> dict:
        attendees = attendees or []
        payload = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_at.isoformat()},
            "end": {"dateTime": end_at.isoformat()},
            "attendees": [{"email": attendee} for attendee in attendees],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.GOOGLE_CALENDAR_API,
                headers=_headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return {
            "id": data.get("id"),
            "html_link": data.get("htmlLink"),
            "status": data.get("status"),
        }

    async def load_google_calendar_events(
        self, 
        scope: str = "today"
    ) -> list[dict]:
        """Load events from Google Calendar with an optional timeframe filter."""
        time_min, time_max = calendar_service._time_bounds(scope)
        params = {
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": 100,
        }
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.GOOGLE_CALENDAR_API,
                headers=_headers(),
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        return [
            {
                "source": "google_calendar",
                "id": item.get("id"),
                "title": item.get("summary", ""),
                "description": item.get("description", ""),
                "start_at": item.get("start", {}).get("dateTime") or item.get("start", {}).get("date"),
                "end_at": item.get("end", {}).get("dateTime") or item.get("end", {}).get("date"),
                "status": item.get("status", ""),
                "html_link": item.get("htmlLink"),
            }
            for item in data.get("items", [])
        ]