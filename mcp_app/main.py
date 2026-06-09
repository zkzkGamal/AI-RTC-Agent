import uvicorn , logging

from server import build_sse_app, mcp
import tools
from tools.stt import preload_model
from get_token import gen_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_DESCRIPTION="""
This is the main entry point for the MCP application. 
It sets up the server, loads necessary tools, and starts the application. 
The `preload_model` function is called to warm up the shared Whisper model used by the audio service, 
    ensuring faster response times for speech-to-text operations. The application is designed to be modular, 
    allowing for easy integration of various tools and services as needed. 
To generate a token for Gmail API access, run the `gen_token` function once locally, which will guide you through the OAuth flow and save the token in a `token.json` file for future use.
"""

if __name__ == "__main__":
    logger.info("Starting MCP application...")
    logger.info(_DESCRIPTION)
    logger.info("revock the google token if you are testing the calendar tool and have made changes to the scopes or credentials.")
    gen_token()
    logger.info("Google token generated successfully. Starting server...")
    preload_model()
    uvicorn.run(
        build_sse_app(),
        host=mcp.settings.host,
        port=mcp.settings.port,
        log_level=mcp.settings.log_level.lower(),
    )
