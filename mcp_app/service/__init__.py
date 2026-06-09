"""
Service module for the MCP (Multi-Component Platform). This module contains various services that provide functionality to the MCP tools. Each service is designed to handle specific tasks and can be used by multiple tools within the MCP.
The services in this module include:
- Calendar Service: Provides methods for handling calendar events, including time parsing and validation.
- Google Calendar Service: Provides methods for interacting with the Google Calendar API, including creating and loading events.
- Calendar ICS Service: Provides methods for handling ICS calendar events, including building ICS event strings and parsing ICS content.
- Create Header Service: Provides a method for creating authorization headers for API calls, specifically for Google Calendar API.
Each service is designed to be modular and reusable, allowing for easy integration into various tools within the MCP. The services also include error handling and logging to ensure that any issues are properly captured and can be debugged effectively.
"""

from .CalnderService import calendar_service
from .CalendarGoogleService import google_calendar_service
from .CalendarICSService import calender_ics_service
from .create_header import _headers

__all__ = ["calendar_service", "google_calendar_service", "calender_ics_service", "_headers"]