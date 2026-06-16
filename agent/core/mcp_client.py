"""agent.core.mcp_client module."""

import sys
import os
import logging

_orig_path = sys.path.copy()
_orig_mcp_modules = {k: v for k, v in sys.modules.items() if k == "mcp" or k.startswith("mcp.")}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
try:
    sys.path = [p for p in sys.path if os.path.basename(p.rstrip("/")) not in ("AI-RTC-Agent", "")]
    for k in list(_orig_mcp_modules.keys()):
        sys.modules.pop(k, None)

    from mcp.client.sse import sse_client
    from mcp.client.session import ClientSession
except Exception as e:
    logger.error(f"Failed to import third-party mcp package: {e}")
    raise e
finally:
    sys.path = _orig_path
    sys.modules.update(_orig_mcp_modules)


from core.auth import api_key_generator_instance


logger = logging.getLogger(__name__)

async def call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """
    Asynchronously call a tool on the FastMCP server with time-locked authentication.
    """
    api_key = api_key_generator_instance.generate_api_key()
    logger.info(f"Invoking MCP tool '{tool_name}' with args {arguments}")
    try:
        async with sse_client(
            "http://localhost:8005/sse", headers={"X-API-Key": api_key}
        ) as (read, write):
            async with ClientSession(read, write) as mcp_session:
                await mcp_session.initialize()
                response = await mcp_session.call_tool(tool_name, arguments)
                if response and response.content:
                    result_text = response.content[0].text
                    logger.info(f"MCP tool '{tool_name}' returned: {result_text[:120]}...")
                    return result_text
                return "Empty response from tool."
    except Exception as e:
        logger.error(f"Error calling MCP tool '{tool_name}': {e}")
        return f"Error executing tool '{tool_name}' via MCP: {e}"
