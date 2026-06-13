import os
import pathlib
import sys
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio

# Setup paths for local package resolution
project_root = pathlib.Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root.parent))
sys.path.insert(0, str(project_root))

from agent.api import router
from agent.sockets.sio import sio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Force AGENT_MODE to 'hr' or load from env if set
os.environ["AGENT_MODE"] = os.environ.get("AGENT_MODE", "hr")

# Create FastAPI app
app = FastAPI(title="AI Agent API Server", version="1.0.0")

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the HTTP API router
app.include_router(router)

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
            
            print("\033[1;30mAgent is thinking...\033[0m")
            res = await chat_service.send_message(
                user_id=user_id,
                session_id=session_id,
                message=user_msg
            )
            
            # Print response or pending confirmation
            if res.get("pending_confirmation"):
                pending = res["pending_confirmation"]
                print(f"\n\033[1;33m⚠️  Human-In-The-Loop Confirmation Required:\033[0m")
                print(f"Tool: \033[1;36m{pending['tool_name']}\033[0m")
                print(f"Arguments:")
                for k, v in pending["arguments"].items():
                    print(f"  - {k}: {v}")
                print("\nOptions: Approve (y), Reject (n), or type your feedback to modify parameters.")
            else:
                print(f"\n\033[1;32mAgent > \033[0m{res['response']}")
        except KeyboardInterrupt:
            print("\n\033[1;31mSession interrupted. Goodbye!\033[0m")
            break
        except Exception as e:
            print(f"\033[1;31mError: {e}\033[0m")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "chat":
        import asyncio
        asyncio.run(run_chat_cli())
    else:
        print("\033[1;31mUsage:\033[0m")
        print("  - To run in CLI chat mode:   python main.py chat")
        print("  - To run the API server:     uvicorn main:socket_app --host 0.0.0.0 --port 8001 --workers 1")
