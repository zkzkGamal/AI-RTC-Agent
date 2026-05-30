"""
MCPApiKeyMiddleware is an ASGI middleware that validates incoming HTTP requests for a valid API key in the "X-API-Key" header.
It uses the api_key_generator class to validate the API key format and expiration. 
Unauthorized requests receive a 401 response, while authorized requests are passed through to the next middleware or endpoint.
"""
import logging
from collections.abc import Callable

from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from .ApiKeyGenerator import api_key_generator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_key_generator_instance = api_key_generator()


class MCPApiKeyMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        validator: Callable[[str], bool] | None = None,
        exempt_paths: set[str] | None = None,
    ) -> None:
        self.app = app
        self.validator = validator or api_key_generator_instance.validate_api_key
        self.exempt_paths = exempt_paths or set()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in self.exempt_paths:
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        if self._is_authorized(headers.get("X-API-Key")):
            self._log_access(scope, authorized=True)
            await self.app(scope, receive, send)
            return

        self._log_access(scope, authorized=False)
        response = JSONResponse({"error": "Unauthorized"}, status_code=401)
        await response(scope, receive, send)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Compatibility helper for direct unit tests.

        Runtime requests use the ASGI __call__ path above. Avoiding
        BaseHTTPMiddleware keeps MCP's SSE stream messages intact.
        """
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        if not self._is_authorized(request.headers.get("X-API-Key")):
            self._log_access(request.scope, authorized=False)
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        self._log_access(request.scope, authorized=True)
        return await call_next(request)

    def _is_authorized(self, api_key: str | None) -> bool:
        return bool(api_key and self.validator(api_key))

    def _log_access(self, scope: Scope, authorized: bool) -> None:
        client = scope.get("client")
        host = client[0] if client else "unknown"
        if authorized:
            logger.info(f"Authorized access from {host}")
        else:
            logger.warning(f"Unauthorized access attempt from {host}")
