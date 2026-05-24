"""
Enforces a consistent response shape across ALL tools.
Every @mcp.tool() function should return through one of these helpers.

Usage:
    from tools.utils.response_parser import ok, err, paginated

    return ok(data={"email_id": "123"}, message="Email sent.")
    return err(message="Failed to connect.", code="CONNECTION_ERROR")
"""

from datetime import datetime, timezone
from typing import Any


def _base(status: str) -> dict:
    return {
        "status":    status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def ok(data: Any = None, message: str = "") -> dict:
    """
    Success response.

    Returns:
        {
            "status":    "ok",
            "timestamp": "...",
            "message":   "Email sent.",
            "data":      { ... }
        }
    """
    response = _base("ok")
    if message:
        response["message"] = message
    if data is not None:
        response["data"] = data
    return response


def err(message: str, code: str = "TOOL_ERROR", details: Any = None) -> dict:
    """
    Error response — use inside except blocks.

    Returns:
        {
            "status":  "error",
            "timestamp": "...",
            "error": {
                "code":    "AUTH_ERROR",
                "message": "Missing Gmail token.",
                "details": { ... }
            }
        }
    """
    response = _base("error")
    response["error"] = {"code": code, "message": message}
    if details is not None:
        response["error"]["details"] = details
    return response


def paginated(items: list, total: int, page: int = 1, page_size: int = 10) -> dict:
    """
    Paginated list response — use for inbox listing, search results, etc.

    Returns:
        {
            "status": "ok",
            "timestamp": "...",
            "data": {
                "items":     [ ... ],
                "total":     42,
                "page":      1,
                "page_size": 10,
                "has_more":  true
            }
        }
    """
    response = _base("ok")
    response["data"] = {
        "items":     items,
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "has_more":  (page * page_size) < total,
    }
    return response


def from_exception(exc: Exception) -> dict:
    """
    Auto-convert any of our custom exceptions to an error response.
    Use in a generic except block at the top of your tool.

    Example:
        try:
            ...
        except Exception as e:
            return from_exception(e)
    """
    from utils.exceptions import (
        AuthError, RateLimitError, ExternalAPIError, ValidationError, ToolError
    )

    if isinstance(exc, AuthError):
        return err(str(exc), code="AUTH_ERROR")
    if isinstance(exc, RateLimitError):
        return err(str(exc), code="RATE_LIMIT", details={"retry_after": exc.retry_after})
    if isinstance(exc, ExternalAPIError):
        return err(str(exc), code="EXTERNAL_API_ERROR", details={"status_code": exc.status_code})
    if isinstance(exc, ValidationError):
        return err(str(exc), code="VALIDATION_ERROR")
    if isinstance(exc, ToolError):
        return err(str(exc), code="TOOL_ERROR")

    return err(f"Unexpected error: {str(exc)}", code="INTERNAL_ERROR")