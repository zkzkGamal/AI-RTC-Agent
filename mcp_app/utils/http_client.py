"""
Shared HTTP client used by all tools.
Handles retries, timeouts, and maps HTTP errors to our custom exceptions.

Usage:
    from tools.utils.http_client import get, post

    data = await get("https://localhost:8005/data", headers={"Authorization": "Bearer ..."})
    data = await post("https://localhost:8005/send", json={"key": "value"})
"""

import asyncio
import httpx

from .exceptions import ExternalAPIError, RateLimitError

TIMEOUT         = 10.0
MAX_RETRIES     = 3
RETRY_BACKOFF   = 2.0

DEFAULT_HEADERS = {
    "User-Agent":   "AI-RTC-Agent/1.0",
    "Accept":       "application/json",
    "Content-Type": "application/json",
}


async def _request(
    method:  str,
    url:     str,
    tool_name: str = "http_client",
    **kwargs,
) -> dict:
    headers = {**DEFAULT_HEADERS, **kwargs.pop("headers", {})}
    attempt = 0

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        while attempt < MAX_RETRIES:
            try:
                response = await client.request(method, url, headers=headers, **kwargs)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise RateLimitError(tool_name=tool_name, retry_after=retry_after)

                if response.status_code in (401, 403):
                    raise ExternalAPIError(
                        message="Authentication failed. Check your credentials.",
                        tool_name=tool_name,
                        status_code=response.status_code,
                    )

                if response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        message=str(response.status_code),
                        request=response.request,
                        response=response,
                    )

                response.raise_for_status()
                return response.json()

            except (httpx.TimeoutException, httpx.HTTPStatusError):
                attempt += 1
                if attempt >= MAX_RETRIES:
                    raise ExternalAPIError(
                        message=f"Request failed after {MAX_RETRIES} attempts.",
                        tool_name=tool_name,
                        status_code=getattr(response, "status_code", None),
                    )
                await asyncio.sleep(RETRY_BACKOFF * attempt)

            except (RateLimitError, ExternalAPIError):
                raise


async def get(url: str, tool_name: str = "http_client", **kwargs) -> dict:
    return await _request("GET", url, tool_name=tool_name, **kwargs)


async def post(url: str, tool_name: str = "http_client", **kwargs) -> dict:
    return await _request("POST", url, tool_name=tool_name, **kwargs)


async def patch(url: str, tool_name: str = "http_client", **kwargs) -> dict:
    return await _request("PATCH", url, tool_name=tool_name, **kwargs)


async def delete(url: str, tool_name: str = "http_client", **kwargs) -> dict:
    return await _request("DELETE", url, tool_name=tool_name, **kwargs)
