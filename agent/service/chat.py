import uuid
import logging
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from agent.agent.agent import graph
from agent.sockets.sio import active_user_id, active_session_id
from agent.service.db import (
    init_db,
    save_session,
    get_session,
    save_message,
    get_messages_by_session,
    get_sessions_by_user
)
from agent.service.cv_memory import (
    ingest_cv,
    cv_memory_system_message,
    window_messages,
)
from core.content_store import save_bytes, read_document

logger = logging.getLogger(__name__)

class Chat:
    def __init__(self):
        # Automatically initialize the database on startup
        try:
            init_db()
            logger.info("SQLite database initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    async def send_message(self, user_id: str, session_id: Optional[str], message: str) -> Dict[str, Any]:
        """
        Sends a message to the agent, running the graph, tracking history, 
        and updating the SQLite database.
        """
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.info(f"Generated new session ID: {session_id} for user: {user_id}")

        # Ensure session exists in the database
        session = get_session(session_id)
        if not session:
            save_session(session_id, user_id)
            session = {"session_id": session_id, "user_id": user_id, "pending_confirmation": None}

        # 1. Save user message to database first
        save_message(session_id, user_id, "human", message)

        # 2. Load the full message history from the database
        db_messages = get_messages_by_session(session_id)
        
        # 3. Convert database messages to LangChain message objects
        lc_messages = []
        for msg in db_messages:
            role = msg["role"]
            content = msg["content"]
            name = msg.get("name")
            tool_call_id = msg.get("tool_call_id")

            if role == "human":
                lc_messages.append(HumanMessage(content=content))
            elif role == "ai":
                lc_messages.append(AIMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "tool":
                lc_messages.append(ToolMessage(content=content, name=name, tool_call_id=tool_call_id))

        agent_messages = window_messages(lc_messages)
        cv_message = cv_memory_system_message(user_id)
        if cv_message is not None:
            agent_messages = [cv_message] + agent_messages

        token_user = active_user_id.set(user_id)
        token_session = active_session_id.set(session_id)

        try:
            state = {
                "messages": agent_messages,
                "user_message": message,
                "route": None,
                "plan": None,
                "tool_calls": None,
                "tool_results": None,
                "pending_confirmation": session.get("pending_confirmation"),
                "error": None
            }

            # Run the agent graph
            result = await graph.ainvoke(state)

            # 5. Extract and save NEW messages generated during this graph execution
            # The new messages are those appended after the windowed history we passed in
            new_messages = result["messages"][len(agent_messages):]
            for msg in new_messages:
                role = "system"
                name = None
                tool_call_id = None

                if isinstance(msg, HumanMessage):
                    role = "human"
                elif isinstance(msg, AIMessage):
                    role = "ai"
                elif isinstance(msg, SystemMessage):
                    role = "system"
                elif isinstance(msg, ToolMessage):
                    role = "tool"
                    name = getattr(msg, "name", None)
                    tool_call_id = getattr(msg, "tool_call_id", None)

                save_message(
                    session_id=session_id,
                    user_id=user_id,
                    role=role,
                    content=msg.content if isinstance(msg.content, str) else str(msg.content),
                    name=name,
                    tool_call_id=tool_call_id
                )

            # 6. Update pending_confirmation state in the session
            new_pending = result.get("pending_confirmation")
            save_session(session_id, user_id, pending_confirmation=new_pending)

            # The final response is the content of the last AIMessage or a conversational output
            final_response = ""
            for msg in reversed(result["messages"]):
                if isinstance(msg, AIMessage) and msg.content:
                    final_response = msg.content
                    break

            return {
                "session_id": session_id,
                "user_id": user_id,
                "response": final_response,
                "pending_confirmation": new_pending,
                "messages_count": len(result["messages"])
            }

        except Exception as e:
            logger.error(f"Error during agent invocation: {e}", exc_info=True)
            raise e
        finally:
            # Reset context variables
            active_user_id.reset(token_user)
            active_session_id.reset(token_session)

    async def ingest_cv_upload(self, user_id: str, filename: str, data: bytes) -> Dict[str, Any]:
        """
        Save an uploaded CV into the global content/ folder, read it (PDF/Word/MD),
        extract keywords + structured knowledge via the LLM, and persist it as the
        user's CV memory. Returns the extracted profile for the frontend.
        """
        if not data:
            raise ValueError("Uploaded file is empty.")

        saved_path = save_bytes(filename, data)          # validates supported type
        cv_text = read_document(str(saved_path))         # PDF / Word / Markdown only

        result = await ingest_cv(
            user_id=user_id,
            file_name=saved_path.name,
            file_path=str(saved_path),
            cv_text=cv_text,
        )
        logger.info(f"Ingested CV '{saved_path.name}' for user '{user_id}'.")
        return {
            "user_id": user_id,
            "file_name": result["file_name"],
            "keywords": result["keywords"],
            "summary": result["summary"],
            "knowledge": result["knowledge"],
        }

    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve all sessions belonging to a user ID."""
        return get_sessions_by_user(user_id)

    def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve the messages list for a given session ID."""
        return get_messages_by_session(session_id)
