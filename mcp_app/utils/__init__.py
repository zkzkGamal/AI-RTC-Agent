"""Shared utilities for the MCP server."""

from .exceptions      import ToolError, AuthError, RateLimitError, ExternalAPIError, ValidationError
from .auth            import credentials
from .http_client     import get, post, patch, delete
from .rate_limiter    import rate_limiter
from .response_parser import ok, err, paginated, from_exception