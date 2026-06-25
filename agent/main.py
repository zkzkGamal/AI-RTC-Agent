"""agent.main module."""

import os
import pathlib
import sys
import logging
import uvicorn
import socketio
from starlette.routing import Router as StarletteRouter


_original_router_init = StarletteRouter.__init__


def _compat_router_init(self, *args, **kwargs):
    kwargs.pop("on_startup", None)
    kwargs.pop("on_shutdown", None)
    return _original_router_init(self, *args, **kwargs)


StarletteRouter.__init__ = _compat_router_init

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

project_root = pathlib.Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root.parent))
sys.path.insert(0, str(project_root))

from agent.api import register_routes
from agent.sockets.sio import sio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool):
    """
    Gate log output behind the verbose flag.
    Quiet mode (default): only WARNING+ is shown, so the chat stays clean.
    Verbose mode: full INFO logging (router/planner/tool traces, httpx, etc.).
    """
    level = logging.INFO if verbose else logging.WARNING
    logging.getLogger().setLevel(level)
    for noisy in ("httpx", "httpcore", "core.mcp_client", "uvicorn"):
        logging.getLogger(noisy).setLevel(level)

os.environ["AGENT_MODE"] = os.environ.get("AGENT_MODE", "hr")

app = FastAPI(title="AI Agent API Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_routes(app)

socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

async def run_chat_cli():
    import asyncio
    from agent.service.chat import Chat
    chat_service = Chat()
    user_id = "cli_user_999"
    session_id = "cli_session_999"

    print("\n" + "\033[1;36m" + "="*60 + "\033[0m")
    print("        🤖 \033[1;35mAI-RTC-AGENT CHAT MODE ACTIVE (CLI Terminal)\033[0m        ")
    print(f"   User ID: \033[1;33m{user_id}\033[0m | Session ID: \033[1;33m{session_id}\033[0m")
    print("   Type \033[1;31m'exit'\033[0m or \033[1;31m'quit'\033[0m to close the session.   ")
    print("\033[1;36m" + "="*60 + "\033[0m\n")

    while True:
        try:
            user_msg = input("\033[1;34mYou > \033[0m")
            if not user_msg.strip():
                continue
            if user_msg.lower() in ["exit", "quit"]:
                print("\033[1;31mGoodbye!\033[0m")
                break

            print("\033[1;30mAgent is thinking...\033[0m", end="", flush=True)

            res = None
            streamed = False
            async for ev in chat_service.send_message_stream(
                user_id=user_id,
                session_id=session_id,
                message=user_msg
            ):
                if ev["type"] == "token":
                    if not streamed:
                        # Clear the "thinking" line and start the answer.
                        print("\r\033[K\033[1;32mAgent > \033[0m", end="", flush=True)
                        streamed = True
                    print(ev["content"], end="", flush=True)
                elif ev["type"] == "final":
                    res = ev

            if streamed:
                print()  # newline after the streamed answer

            res = res or {}
            if res.get("pending_confirmation"):
                if not streamed:
                    print("\r\033[K", end="")  # clear the "thinking" line
                pending = res["pending_confirmation"]
                print(f"\n\033[1;33m⚠️  Human-In-The-Loop Confirmation Required:\033[0m")
                print(f"Tool: \033[1;36m{pending['tool_name']}\033[0m")
                print(f"Arguments:")
                for k, v in pending["arguments"].items():
                    print(f"  - {k}: {v}")
                print("\nOptions: Approve (y), Reject (n), or type your feedback to modify parameters.")
            elif not streamed:
                # No tokens streamed (e.g. empty response) — fall back to printing it.
                print(f"\r\033[K\n\033[1;32mAgent > \033[0m{res.get('response', '')}")
        except KeyboardInterrupt:
            print("\n\033[1;31mSession interrupted. Goodbye!\033[0m")
            break
        except Exception as e:
            print(f"\033[1;31mError: {e}\033[0m")

if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    verbose = any(a in ("-v", "--verbose") for a in args)
    positional = [a for a in args if not a.startswith("-")]

    if positional and positional[0] == "chat":
        _configure_logging(verbose)
        import asyncio
        asyncio.run(run_chat_cli())
    else:
        print("\033[1;31mUsage:\033[0m")
        print("  - To run in CLI chat mode:   python main.py chat [-v|--verbose]")
        print("  - To run the API server:     uvicorn main:socket_app --host 0.0.0.0 --port 8001 --workers 1")
