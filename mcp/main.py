from server import mcp
import tools
from tools.stt import preload_model

if __name__ == "__main__":
    preload_model()
    mcp.run(transport="sse")
