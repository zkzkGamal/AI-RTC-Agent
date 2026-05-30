import pytest
from starlette.requests import Request
from starlette.responses import Response

import server as server_module
from core.ApiKeyGenerator import api_key_generator
from core.Middleware import MCPApiKeyMiddleware


def test_api_key_generator_round_trip():
    generator = api_key_generator(expire_time=5)
    api_key = generator.generate_api_key()

    assert generator.validate_api_key(api_key) is True


def test_api_key_generator_rejects_invalid_format():
    generator = api_key_generator(expire_time=5)

    assert generator.validate_api_key("not-a-real-key") is False


def test_api_key_generator_rejects_old_key(monkeypatch):
    generator = api_key_generator(expire_time=5)
    old_bucket = 100
    api_key = f"{generator.generate_suffix(old_bucket)}_{old_bucket}_{generator.generate_prefix(old_bucket)}"

    monkeypatch.setattr(generator, "create_value", lambda at_time=None: 103)

    assert generator.validate_api_key(api_key, grace_windows=1) is False


@pytest.mark.asyncio
async def test_api_key_middleware_accepts_valid_key():
    middleware = MCPApiKeyMiddleware(app=lambda scope, receive, send: None, validator=lambda api_key: api_key == "valid-key")
    request = _request_with_headers({"X-API-Key": "valid-key"})

    async def call_next(req):
        return Response("ok", status_code=200)

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    assert response.body == b"ok"


@pytest.mark.asyncio
async def test_api_key_middleware_rejects_missing_key():
    middleware = MCPApiKeyMiddleware(app=lambda scope, receive, send: None, validator=lambda api_key: True)
    request = _request_with_headers()

    async def call_next(req):
        raise AssertionError("call_next should not be reached for unauthorized requests")

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 401
    assert response.body == b'{"error":"Unauthorized"}'


@pytest.mark.asyncio
async def test_api_key_middleware_rejects_invalid_key():
    middleware = MCPApiKeyMiddleware(app=lambda scope, receive, send: None, validator=lambda api_key: False)
    request = _request_with_headers({"X-API-Key": "bad-key"})

    async def call_next(req):
        raise AssertionError("call_next should not be reached for unauthorized requests")

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 401
    assert response.body == b'{"error":"Unauthorized"}'


def test_build_sse_app_registers_api_key_middleware():
    app = server_module.build_sse_app()

    assert any(m.cls is MCPApiKeyMiddleware for m in app.user_middleware)


@pytest.mark.asyncio
async def test_api_key_middleware_passes_asgi_messages_without_buffering():
    messages = []

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    middleware = MCPApiKeyMiddleware(app=app, validator=lambda api_key: api_key == "valid-key")
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/sse",
        "headers": [(b"x-api-key", b"valid-key")],
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    await middleware(scope, receive, send)

    assert messages == [
        {"type": "http.response.start", "status": 200, "headers": []},
        {"type": "http.response.body", "body": b"", "more_body": False},
    ]


def _request_with_headers(headers: dict[str, str] | None = None) -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/sse",
        "headers": raw_headers,
    }
    return Request(scope)
