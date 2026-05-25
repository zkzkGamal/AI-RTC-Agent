from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .ApiKeyGenerator import api_key_generator

api_key_generator_instance = api_key_generator()


class MCPApiKeyMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        validator: Callable[[str], bool] | None = None,
        exempt_paths: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.validator = validator or api_key_generator_instance.validate_api_key
        self.exempt_paths = exempt_paths or set()

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key or not self.validator(api_key):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        return await call_next(request)
