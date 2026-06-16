"""mcp_app.server module."""

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette

from core.Middleware import MCPApiKeyMiddleware, api_key_generator_instance

mcp = FastMCP("AI-RTC-Agent" , port=8005)


def build_sse_app() -> Starlette:
    app = mcp.sse_app()
    app.add_middleware(
        MCPApiKeyMiddleware,
        validator=api_key_generator_instance.validate_api_key,
    )
    return app
