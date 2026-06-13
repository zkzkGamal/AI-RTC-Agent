import asyncio
import aiohttp
import socketio
import logging
import sys
import os
import pathlib
import uuid

# Setup paths
project_root = pathlib.Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root.parent.parent)) # Add AI-RTC-Agent root
sys.path.insert(0, str(project_root.parent))        # Add agent folder root
sys.path.insert(0, str(project_root))               # Add tests folder root

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_flow():
    # Clear the persistent agent database so we start with a clean state
    db_file = project_root.parent / "agent.db"
    if db_file.exists():
        try:
            db_file.unlink()
            logger.info("Cleared existing SQLite database file for clean test run.")
        except Exception as e:
            logger.error(f"Failed to clear database file: {e}")

    # Start the server in the background
    import uvicorn
    from agent.main import socket_app
    
    # Run on a high port to avoid conflicts
    config = uvicorn.Config(socket_app, host="127.0.0.1", port=8001, log_level="info")
    server = uvicorn.Server(config)
    
    server_task = asyncio.create_task(server.serve())
    await asyncio.sleep(2) # Give server time to start
    
    # Initialize Socket.IO Client
    sio_client = socketio.AsyncClient()
    
    received_events = []
    
    # Listen to events
    @sio_client.on("tool_start")
    async def on_tool_start(data):
        logger.info(f"[CLIENT] Received tool_start socket event: {data}")
        received_events.append(("tool_start", data))
        
    @sio_client.on("tool_finished")
    async def on_tool_finished(data):
        logger.info(f"[CLIENT] Received tool_finished socket event: {data}")
        received_events.append(("tool_finished", data))

    try:
        # Connect to Socket.IO
        logger.info("Connecting socket client to http://localhost:8001")
        await sio_client.connect("http://localhost:8001")
        
        # Join session and user rooms
        user_id = "test_user_123"
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        await sio_client.emit("join", {"user_id": user_id, "session_id": session_id})
        await asyncio.sleep(0.5)
        
        # Send a message that triggers a tool call (like duckduckgo_search)
        logger.info("Sending chat request to http://localhost:8001/api/chat")
        async with aiohttp.ClientSession() as session:
            payload = {
                "user_id": user_id,
                "session_id": session_id,
                "message": "Search duckduckgo for Google Gemini updates"
            }
            async with session.post("http://localhost:8001/api/chat", json=payload) as resp:
                result = await resp.json()
                logger.info(f"Chat API response: {result}")
                
        # Wait a bit to ensure all socket events are processed
        await asyncio.sleep(5)
        
        # Validate that the database has saved the session and messages
        logger.info("Verifying database storage via GET /api/sessions/{user_id} and GET /api/sessions/{session_id}/messages")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:8001/api/sessions/{user_id}") as resp:
                sessions_res = await resp.json()
                logger.info(f"User Sessions: {sessions_res}")
                assert len(sessions_res["sessions"]) > 0
                
            async with session.get(f"http://localhost:8001/api/sessions/{session_id}/messages") as resp:
                messages_res = await resp.json()
                logger.info(f"Session Messages: {messages_res}")
                assert len(messages_res["messages"]) >= 2
        
        logger.info("====================================")
        logger.info(f"Total socket events received: {len(received_events)}")
        for name, data in received_events:
            logger.info(f"Event: {name} -> {data}")
        logger.info("====================================")
        
        logger.info("API AND WS TEST PASSED SUCCESSFULLY!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise e
    finally:
        await sio_client.disconnect()
        server.should_exit = True
        await server_task

if __name__ == "__main__":
    os.environ["AGENT_MODE"] = "hr"
    asyncio.run(test_flow())
