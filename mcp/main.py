import uvicorn

from server import build_sse_app, mcp
import tools
from tools.stt import preload_model


if __name__ == "__main__":
    preload_model()
    uvicorn.run(
        build_sse_app(),
        host=mcp.settings.host,
        port=mcp.settings.port,
        log_level=mcp.settings.log_level.lower(),
    )
