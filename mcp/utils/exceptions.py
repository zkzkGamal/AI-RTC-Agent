"""
All custom exceptions for the MCP tools layer.
Catch these in your @mcp.tool() functions for clean error responses.
"""


class ToolError(Exception):
    """Base exception for all tool errors."""
    def __init__(self, message: str, tool_name: str = "unknown"):
        self.tool_name = tool_name
        super().__init__(f"[{tool_name}] {message}")


class AuthError(ToolError):
    """Raised when credentials are missing, invalid, or expired."""
    pass


class RateLimitError(ToolError):
    """Raised when an external API rate limit is hit."""
    def __init__(self, tool_name: str = "unknown", retry_after: int | None = None):
        self.retry_after = retry_after
        msg = "Rate limit hit."
        if retry_after:
            msg += f" Retry after {retry_after}s."
        super().__init__(msg, tool_name)


class ExternalAPIError(ToolError):
    """Raised when an external API returns an unexpected error."""
    def __init__(self, message: str, tool_name: str = "unknown", status_code: int | None = None):
        self.status_code = status_code
        super().__init__(f"{message} (HTTP {status_code})" if status_code else message, tool_name)


class ValidationError(ToolError):
    """Raised when tool input arguments fail validation."""
    pass