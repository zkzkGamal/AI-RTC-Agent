"""
Service for handling ICS calendar events.
This service provides methods to build ICS event strings and parse ICS content.
It is used as a fallback in calendar tools when Google Calendar API calls fail.
"""
import logging
import uuid
from datetime import datetime

from icalendar import Calendar, Event

from .CalnderService import calendar_service

calendar_service = calendar_service()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class calender_ics_service:
    def __init__(self):
        """
        How to use:
        1. Call build_ics_event to create an ICS string for a calendar event, providing title, start/end times, description, and attendees.
        2. Call load_ics_events to parse raw ICS content and extract event details, optionally filtering by scope (e.g., "today").
        3. The tools using this service will handle exceptions gracefully, logging any errors encountered during ICS parsing or generation and returning fallback values as needed.
        args:
            title: The event title/summary.
            start_at: The event start time as a datetime object.
            end_at: The event end time as a datetime object.
            description: Optional event description.
            attendees: Optional list of attendee email addresses.
        """
        pass

    def load_ics_events(
        self ,
        ics_content: str, 
        scope: str = "today"
        ) -> list[dict]:
        """Parse ICS content and return normalized events."""
        try:
            calendar = Calendar.from_ical(ics_content)
            events = []

            for component in calendar.walk():
                if component.name != "VEVENT":
                    continue

                start_value = component.decoded("dtstart", None)
                end_value = component.decoded("dtend", None)

                if start_value is None or not calendar_service._event_in_scope(start_value, scope):
                    continue

                events.append(
                    {
                        "source": "ics",
                        "id": str(component.get("uid", "")),
                        "title": str(component.get("summary", "")),
                        "description": str(component.get("description", "")),
                        "start_at": calendar_service._to_iso(start_value),
                        "end_at": calendar_service._to_iso(end_value) if end_value is not None else None,
                        "status": str(component.get("status", "")),
                    }
                )

            return sorted(events, key=lambda item: item.get("start_at") or "")
        except Exception as exc:
            events = []
            logger.error("Failed to parse ICS content. Error: %s", exc)
            return events

    def build_ics_event(
        self,
        title: str,
        start_at: datetime,
        end_at: datetime,
        description: str = "",
        attendees: list[str] | None = None,
    ) -> str:
        try:
            attendees = attendees or []

            calendar = Calendar()
            calendar.add("prodid", "-//AI-RTC-Agent//Google Calendar MCP Tool//EN")
            calendar.add("version", "2.0")

            event = Event()
            event.add("summary", title)
            event.add("description", description)
            event.add("dtstart", start_at)
            event.add("dtend", end_at)
            event.add("dtstamp", datetime.utcnow())
            event.add("uid", str(uuid.uuid4()))
            event.add("created", datetime.utcnow())
            event.add("last-modified", datetime.utcnow())
            event.add("status", "CONFIRMED")

            for attendee in attendees:
                event.add("attendee", attendee)

            calendar.add_component(event)
            return calendar.to_ical().decode("utf-8")
        except Exception as exc:
            logger.error("Failed to build ICS event. Error: %s", exc)
            return "Failed to generate ICS event."

