import importlib

import pytest

create_module = importlib.import_module("tools.calendar.create_event")
load_module = importlib.import_module("tools.calendar.load_event")

from tools.calendar.create_event import create_calendar_event
from tools.calendar.load_event import load_calendar_events


@pytest.mark.asyncio
async def test_create_calendar_event_google_success(monkeypatch):
    """Test Google Calendar event creation success response."""
    captured = {}

    async def fake_acquire(tool_name: str, hard_fail: bool = False):
        captured["tool_name"] = tool_name

    def fake_parse(date: str, time: str, duration_minutes: int):
        captured["parse_args"] = (date, time, duration_minutes)
        return ("start-dt", "end-dt")

    def fake_build(title, start_at, end_at, description, attendees):
        captured["ics_args"] = (title, start_at, end_at, description, attendees)
        return "BEGIN:VCALENDAR\nEND:VCALENDAR"

    async def fake_google_create(**kwargs):
        captured["google_args"] = kwargs
        return {"id": "evt-1", "html_link": "https://calendar.google.com/e/evt-1", "status": "confirmed"}

    monkeypatch.setattr(create_module.rate_limiter, "acquire", fake_acquire)
    monkeypatch.setattr(create_module.calendar_service, "_parse_event_times", fake_parse)
    monkeypatch.setattr(create_module.calender_ics_service, "build_ics_event", fake_build)
    monkeypatch.setattr(
        create_module.google_calendar_service,
        "create_google_calendar_event",
        fake_google_create,
    )

    result = await create_calendar_event(
        title="Standup",
        date="2026-05-25",
        time="09:00",
        duration_minutes=30,
        description="Daily sync",
        attendees=["a@example.com"],
    )

    assert result["status"] == "ok"
    assert result["data"]["provider"] == "google_calendar"
    assert result["data"]["google_event"]["id"] == "evt-1"
    assert result["data"]["ics"] == "BEGIN:VCALENDAR\nEND:VCALENDAR"
    assert result["data"]["fallback_reason"] is None
    assert captured["tool_name"] == "calendar_create_event"
    assert captured["parse_args"] == ("2026-05-25", "09:00", 30)


@pytest.mark.asyncio
async def test_create_calendar_event_falls_back_to_ics(monkeypatch):
    """Test calendar creation returns ICS fallback when Google fails."""
    async def fake_acquire(tool_name: str, hard_fail: bool = False):
        return None

    def fake_parse(date: str, time: str, duration_minutes: int):
        return ("start-dt", "end-dt")

    def fake_build(title, start_at, end_at, description, attendees):
        return "BEGIN:VCALENDAR\nEND:VCALENDAR"

    async def fake_google_create(**kwargs):
        raise RuntimeError("calendar auth missing")

    monkeypatch.setattr(create_module.rate_limiter, "acquire", fake_acquire)
    monkeypatch.setattr(create_module.calendar_service, "_parse_event_times", fake_parse)
    monkeypatch.setattr(create_module.calender_ics_service, "build_ics_event", fake_build)
    monkeypatch.setattr(
        create_module.google_calendar_service,
        "create_google_calendar_event",
        fake_google_create,
    )

    result = await create_calendar_event(
        title="Standup",
        date="2026-05-25",
        time="09:00",
        duration_minutes=30,
    )

    assert result["status"] == "ok"
    assert result["data"]["provider"] == "ics_fallback"
    assert result["data"]["google_event"] is None
    assert result["data"]["ics"] == "BEGIN:VCALENDAR\nEND:VCALENDAR"
    assert "calendar auth missing" in result["data"]["fallback_reason"]


@pytest.mark.asyncio
async def test_load_calendar_events_merges_google_and_ics(monkeypatch):
    """Test loading events from both Google Calendar and ICS content."""
    captured = {}

    async def fake_acquire(tool_name: str, hard_fail: bool = False):
        captured["tool_name"] = tool_name

    async def fake_google_load(scope: str = "today"):
        captured["google_scope"] = scope
        return [
            {
                "source": "google_calendar",
                "id": "g-1",
                "title": "Google Event",
                "description": "",
                "start_at": "2026-05-25T09:00:00",
                "end_at": "2026-05-25T09:30:00",
                "status": "confirmed",
                "html_link": "https://calendar.google.com/g-1",
            }
        ]

    def fake_ics_load(ics_content: str, scope: str = "today"):
        captured["ics_scope"] = scope
        captured["ics_content"] = ics_content
        return [
            {
                "source": "ics",
                "id": "i-1",
                "title": "ICS Event",
                "description": "",
                "start_at": "2026-05-25T08:00:00",
                "end_at": "2026-05-25T08:30:00",
                "status": "CONFIRMED",
            }
        ]

    monkeypatch.setattr(load_module.rate_limiter, "acquire", fake_acquire)
    monkeypatch.setattr(
        load_module.google_calendar_service,
        "load_google_calendar_events",
        fake_google_load,
    )
    monkeypatch.setattr(load_module.calender_ics_service, "load_ics_events", fake_ics_load)

    result = await load_calendar_events(scope="today", ics_content="BEGIN:VCALENDAR")

    assert result["status"] == "ok"
    assert result["data"]["scope"] == "today"
    assert result["data"]["count"] == 2
    assert result["data"]["sources"] == {"google_calendar": 1, "ics": 1}
    assert [event["id"] for event in result["data"]["events"]] == ["i-1", "g-1"]
    assert captured["tool_name"] == "calendar"
    assert captured["google_scope"] == "today"
    assert captured["ics_scope"] == "today"


@pytest.mark.asyncio
async def test_load_calendar_events_ics_only_when_google_fails(monkeypatch):
    """Test calendar loader still returns ICS events when Google fetch fails."""
    async def fake_acquire(tool_name: str, hard_fail: bool = False):
        return None

    async def fake_google_load(scope: str = "today"):
        raise RuntimeError("token expired")

    def fake_ics_load(ics_content: str, scope: str = "today"):
        return [
            {
                "source": "ics",
                "id": "i-1",
                "title": "ICS Event",
                "description": "",
                "start_at": "2026-05-25T08:00:00",
                "end_at": "2026-05-25T08:30:00",
                "status": "CONFIRMED",
            }
        ]

    monkeypatch.setattr(load_module.rate_limiter, "acquire", fake_acquire)
    monkeypatch.setattr(
        load_module.google_calendar_service,
        "load_google_calendar_events",
        fake_google_load,
    )
    monkeypatch.setattr(load_module.calender_ics_service, "load_ics_events", fake_ics_load)

    result = await load_calendar_events(scope="all", ics_content="BEGIN:VCALENDAR")

    assert result["status"] == "ok"
    assert result["data"]["count"] == 1
    assert result["data"]["sources"] == {"google_calendar": 0, "ics": 1}
    assert "token expired" in result["data"]["google_error"]
