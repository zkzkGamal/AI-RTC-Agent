"""
Service for handling calendar events. 
This service provides methods to convert event times to ISO format, determine time bounds based on scope,
    check if an event is in scope, and parse event times from date, time, and duration inputs. 
It is used by calendar tools to manage event data and ensure proper formatting and validation.   
"""
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

try:
    from mcp.utils.exceptions import ValidationError
except ModuleNotFoundError:
    from utils.exceptions import ValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class calendar_service:
    def __init__(self):
        """
        How to use:
        1. Call _to_iso to convert various date/time inputs to ISO 8601 format for API compatibility.
        2. Call _time_bounds with a scope of "today" or "all" to get the appropriate time range for event filtering.
        3. Call _event_in_scope with an event's start time and a scope to check if the event falls within the desired time frame.
        4. Call _parse_event_times with date, time, and duration inputs to get start and end times as datetime objects, ensuring proper validation and error handling.
        The tools using this service will handle exceptions gracefully, logging any errors encountered during time parsing or validation and returning fallback values as needed.
        args:
            date: The event date in YYYY-MM-DD format.
            time: The event start time in HH:MM (24-hour) format.
            duration_minutes: The event duration in minutes, must be greater than 0.
        """
        pass
    
    def _to_iso(self , value: Any) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return datetime.combine(value, time.min).isoformat()
        return str(value)
    
    def _time_bounds(self , scope: str) -> tuple[str | None, str | None]:
        if scope not in {"today", "all"}:
            raise ValidationError(
                "scope must be either 'today' or 'all'.",
                tool_name="calendar_load_event",
            )

        if scope == "all":
            return None, None

        today = date.today()
        start_of_day = datetime.combine(today, time.min, tzinfo=timezone.utc)
        end_of_day = start_of_day + timedelta(days=1)
        return start_of_day.isoformat(), end_of_day.isoformat()
    
    def _event_in_scope(self , start_value: Any, scope: str) -> bool:
        if scope == "all":
            return True

        today = date.today()
        if isinstance(start_value, datetime):
            return start_value.date() == today
        if isinstance(start_value, date):
            return start_value == today
        return False
    
    def _parse_event_times(self , date: str, time: str, duration_minutes: int) -> tuple[datetime, datetime]:
        if duration_minutes <= 0:
            raise ValidationError(
                "duration_minutes must be greater than 0.",
                tool_name="calendar_create_event",
            )

        try:
            start_at = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        except ValueError as exc:
            raise ValidationError(
                "date must use YYYY-MM-DD and time must use HH:MM (24-hour).",
                tool_name="calendar_create_event",
            ) from exc

        end_at = start_at + timedelta(minutes=duration_minutes)
        return start_at, end_at