import importlib

import pytest

inbox_module = importlib.import_module("tools.emails.check_inbox")
send_module = importlib.import_module("tools.emails.send_mail")

from tools.emails.check_inbox import list_inbox
from tools.emails.send_mail import send_email


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _FakeInboxClient:
    def __init__(self):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, headers=None, params=None):
        self.calls.append({"url": url, "headers": headers, "params": params})

        if url.endswith("/messages"):
            return _FakeResponse(
                {
                    "messages": [
                        {"id": "msg-1"},
                        {"id": "msg-2"},
                    ]
                }
            )

        if url.endswith("/messages/msg-1"):
            return _FakeResponse(
                {
                    "id": "msg-1",
                    "snippet": "First snippet",
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "First subject"},
                            {"name": "From", "value": "sender1@example.com"},
                            {"name": "Date", "value": "Mon, 01 Jan 2026 10:00:00 +0000"},
                        ]
                    },
                }
            )

        if url.endswith("/messages/msg-2"):
            return _FakeResponse(
                {
                    "id": "msg-2",
                    "snippet": "Second snippet",
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Second subject"},
                            {"name": "From", "value": "sender2@example.com"},
                            {"name": "Date", "value": "Tue, 02 Jan 2026 11:00:00 +0000"},
                        ]
                    },
                }
            )

        raise AssertionError(f"Unexpected URL: {url}")


@pytest.mark.asyncio
async def test_list_inbox_success(monkeypatch):
    captured = {}
    fake_client = _FakeInboxClient()

    async def fake_acquire(tool_name: str, hard_fail: bool = False):
        captured["tool_name"] = tool_name
        captured["hard_fail"] = hard_fail

    monkeypatch.setattr(inbox_module.rate_limiter, "acquire", fake_acquire)
    monkeypatch.setattr(inbox_module, "_headers", lambda: {"Authorization": "Bearer test-token"})
    monkeypatch.setattr(inbox_module.httpx, "AsyncClient", lambda: fake_client)

    result = await list_inbox(limit=100)

    assert result["status"] == "ok"
    assert result["data"]["count"] == 2
    assert result["data"]["emails"] == [
        {
            "id": "msg-1",
            "subject": "First subject",
            "from": "sender1@example.com",
            "date": "Mon, 01 Jan 2026 10:00:00 +0000",
            "snippet": "First snippet",
        },
        {
            "id": "msg-2",
            "subject": "Second subject",
            "from": "sender2@example.com",
            "date": "Tue, 02 Jan 2026 11:00:00 +0000",
            "snippet": "Second snippet",
        },
    ]
    assert captured["tool_name"] == "gmail"
    assert fake_client.calls[0]["params"]["maxResults"] == 50


@pytest.mark.asyncio
async def test_send_email_success(monkeypatch):
    captured = {}

    def fake_require(*field_names):
        captured["required_fields"] = field_names

    async def fake_acquire(tool_name: str, hard_fail: bool = False):
        captured["tool_name"] = tool_name

    async def fake_to_thread(func, subject, body, to_email):
        captured["func"] = func
        captured["subject"] = subject
        captured["body"] = body
        captured["to_email"] = to_email
        return None

    monkeypatch.setattr(send_module.credentials, "require", fake_require)
    monkeypatch.setattr(send_module.rate_limiter, "acquire", fake_acquire)
    monkeypatch.setattr(send_module.asyncio, "to_thread", fake_to_thread)

    result = await send_email(
        subject="Test mail",
        body="Hello from pytest",
        to_email=["receiver@example.com"],
    )

    assert result["status"] == "ok"
    assert result["message"] == "Email sent successfully."
    assert result["data"] == {
        "to": ["receiver@example.com"],
        "subject": "Test mail",
    }
    assert captured["required_fields"] == ("MAIL_HOST", "MAIL_USERNAME", "MAIL_PASSWORD")
    assert captured["tool_name"] == "gmail"
    assert captured["func"].__self__ is send_module.mail_service
    assert captured["func"].__func__ is send_module.mail_service._send_sync.__func__
    assert captured["subject"] == "Test mail"
    assert captured["body"] == "Hello from pytest"
    assert captured["to_email"] == ["receiver@example.com"]


@pytest.mark.asyncio
async def test_send_email_empty_recipients():
    result = await send_email(subject="Test mail", body="Hello", to_email=[])

    assert result["status"] == "error"
    assert result["error"]["code"] == "VALIDATION_ERROR"
    assert result["error"]["message"] == "No recipients provided."
