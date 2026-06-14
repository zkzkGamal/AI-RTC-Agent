"""
Execute Node (act.py)
---------------------
Runs the tool calls requested by the agent using a custom ReAct loop.
Includes:
- Human-in-the-Loop (HIL) safety controls for modifying/dangerous actions.
- ReAct loop to handle multi-tool execution and tool call failures.
"""
import pathlib
import logging
import environ
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from agent.llm.load_model import llm
from core.loadPrompts import LoadPrompts
from tools import (
    duckduckgo_search,
    list_inbox,
    read_email,
    send_email,
    reply_to_email,
    draft_reply,
    create_calendar_event,
    load_calendar_events,
    readcv,
)

logger = logging.getLogger(__name__)

try:
    from agent.sockets.sio import sio, active_user_id, active_session_id
except ImportError:
    sio = None
    active_user_id = None
    active_session_id = None

async def emit_tool_event(tool_name: str, status: str, payload_data: dict = None):
    if sio is not None:
        user_id = active_user_id.get() if active_user_id else None
        session_id = active_session_id.get() if active_session_id else None
        try:
            event_payload = {
                "status": status,
                "tool_name": tool_name,
                "user_id": user_id,
                "session_id": session_id,
                **(payload_data or {})
            }
            # Emit to session room
            if session_id:
                await sio.emit(tool_name, event_payload, room=session_id)
                await sio.emit(f"tool_{status}", event_payload, room=session_id)
            # Emit to user room
            if user_id:
                await sio.emit(tool_name, event_payload, room=user_id)
                await sio.emit(f"tool_{status}", event_payload, room=user_id)
            # Broadcast
            await sio.emit(tool_name, event_payload)
            await sio.emit(f"tool_{status}", event_payload)
        except Exception as e:
            logger.error(f"Failed to emit tool socket event: {e}")
load_prompts = LoadPrompts()

_base = pathlib.Path(__file__).parent.parent.parent
_e    = environ.Env()
_e.read_env(str(_base / ".env"))

AGENT_MODE = _e("AGENT_MODE", default="general")

_PARTIAL_PROMPT = load_prompts.load_partial_prompt(f"act/{AGENT_MODE}.yaml")

# Register tools based on AGENT_MODE
_active_tools = [
    duckduckgo_search,
    list_inbox,
    read_email,
    send_email,
    reply_to_email,
    draft_reply,
    create_calendar_event,
    load_calendar_events,
]

if AGENT_MODE == "hr":
    _active_tools.append(readcv)

# Map tools by name for execution lookup
_TOOL_MAP = {t.name: t for t in _active_tools}

# Bind tools to the LLM
llm_with_tools = llm.bind_tools(_active_tools)

# Define dangerous tools that require Human-In-The-Loop approval
DANGEROUS_TOOLS = {"send_email", "reply_to_email", "create_calendar_event"}


async def execute(state: dict) -> dict:
    """
    Execute tools in a ReAct loop.
    Paues and prompts for confirmation if a dangerous tool is triggered.
    """
    messages = list(state.get("messages", []))
    initial_message_count = len(messages)
    pending = state.get("pending_confirmation")
    route = state.get("route", "DIRECT")
    intent = state.get("intent", "CHAT")
    plan = state.get("plan", "")

    # Get details for formatting act system instructions
    user_text = messages[-1].content if messages else ""
    history = messages[:-1]
    conversation_history = "\n".join(
        f"{m.type.upper()}: {m.content}"
        for m in history
        if hasattr(m, "content")
    )
    last_route = state.get("last_route", "")
    last_tool_result = state.get("last_tool_result", "")

    # Format dedicated tool execution system instructions
    plan_section = f"Plan Drafted by Planner:\n{plan}" if plan else ""
    system_instruction = f"""You are the tool execution agent in a multi-agent HR Assistant system.
Your job is to execute the necessary tool calls to fulfill the user's request.

─────────────────────────────────────
INSTRUCTIONS
─────────────────────────────────────
1. Use the available tools (such as searching or sending/replying to emails) to fulfill the user's request:
   - User Request: {user_text}
   - Classified Route: {route}
   - Business Intent: {intent}
2. If the task has multiple steps (for example, "search tech news and email it"), you MUST call the tools sequentially:
   - Step 1: Call `duckduckgo_search` to find the news.
   - Step 2: Once you receive the search results, call `send_email` to email the results to the requested address.
3. If a tool call fails or returns an error, do not loop indefinitely. Try to inform the user or finish.
4. Do NOT call the same tool with the exact same arguments if it has already executed successfully in the conversation history. You should still proceed with subsequent steps and call other required tools sequentially (e.g. call search first, then call email with the search results).
5. Do not output a final text summary until all required tool executions are complete.

{plan_section}
"""
    system_messages = [SystemMessage(content=system_instruction)]

    # 1. Handle pending confirmation response from user if resuming
    if pending:
        import json
        user_msg = messages[-1].content.strip().lower()
        tool_name = pending["tool_name"]
        tool_args = pending["arguments"]
        tool_call_id = pending["id"]

        logger.info(f"[execute] Resuming pending tool '{tool_name}'. User response: '{user_msg}'")

        # Check if the user is requesting modifications to the parameters
        is_modification = False
        words = user_msg.split()
        if len(words) > 1 and any(kw in user_msg for kw in ["make", "change", "instead", "body", "subject", "to", "recipient", "content", "title", "update", "set"]):
            is_modification = True

        is_approved = any(w in user_msg for w in ["approve", "yes", "confirm", "go ahead", "y"]) and not is_modification
        is_rejected = any(w in user_msg for w in ["reject", "no", "cancel", "n"]) and not is_modification

        if is_modification:
            logger.info(f"[execute] User requested modification: '{user_msg}'. Asking LLM to update arguments...")
            system_prompt = f"""You are a precise JSON assistant.
Your job is to update the JSON arguments of an API tool call based on user feedback.

Original Tool: {tool_name}
Original Arguments:
{json.dumps(tool_args, indent=2)}

User Request:
"{messages[-1].content}"

Modify the arguments according to the user request.
Return ONLY the final updated JSON dictionary. Do not include any explanation, backticks, or other text.
"""
            try:
                llm_response = await llm.ainvoke([SystemMessage(content=system_prompt)])
                content = llm_response.content.strip()
                
                # Robust extraction of JSON substring
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = content
                
                updated_args = json.loads(json_str)
                logger.info(f"[execute] Updated tool arguments: {updated_args}")
                
                # Execute tool with updated arguments
                tool_instance = _TOOL_MAP[tool_name]
                await emit_tool_event(tool_name, "start", {"arguments": updated_args})
                result = await tool_instance.ainvoke(updated_args)
                await emit_tool_event(tool_name, "finished", {"result": str(result)})
            except Exception as e:
                logger.error(f"[execute] Failed to modify tool arguments: {e}. Raw response: {content}")
                result = f"Error: Failed to apply modifications: {e}"
        
        elif is_approved:
            try:
                tool_instance = _TOOL_MAP[tool_name]
                logger.info(f"[execute] Tool execution APPROVED. Calling tool '{tool_name}'...")
                await emit_tool_event(tool_name, "start", {"arguments": tool_args})
                result = await tool_instance.ainvoke(tool_args)
                await emit_tool_event(tool_name, "finished", {"result": str(result)})
            except Exception as e:
                logger.error(f"[execute] Tool '{tool_name}' failed: {e}")
                result = f"Error: Tool execution failed: {e}"
        else:
            logger.info(f"[execute] Tool execution REJECTED or unrecognized response.")
            result = "Error: Tool execution rejected by human."

        tool_message = ToolMessage(content=str(result), tool_call_id=tool_call_id)
        messages.append(tool_message)
        pending = None
        state["pending_confirmation"] = None

    max_iterations = 5
    for iteration in range(max_iterations):
        model_inputs = system_messages + messages
        response = await llm_with_tools.ainvoke(model_inputs)

        messages.append(response)

        if not response.tool_calls:
            logger.info("[execute] Reasoning complete. No tool calls requested.")
            break

        logger.info(f"[execute] LLM requested tool calls: {[tc['name'] for tc in response.tool_calls]}")

        dangerous_call = None
        for call in response.tool_calls:
            if call["name"] in DANGEROUS_TOOLS:
                dangerous_call = call
                break

        if dangerous_call:
            pending = {
                "tool_name": dangerous_call["name"],
                "arguments": dangerous_call["args"],
                "id": dangerous_call["id"],
            }
            logger.warning(f"[execute] HIL Triggered! Pausing for dangerous tool: {dangerous_call['name']}")
            
            args_str = ""
            for k, v in dangerous_call["args"].items():
                if isinstance(v, list):
                    v = ", ".join(map(str, v))
                args_str += f"{k}:{v}\n"
            
            pretty_message = f"the response {dangerous_call['name']} the agrs is\n{args_str.strip()}"
            
            messages.append(AIMessage(content=pretty_message))
            
            return {
                "messages": messages,
                "pending_confirmation": pending,
                "tool_results": pretty_message,
            }

        for call in response.tool_calls:
            tool_name = call["name"]
            tool_args = call["args"]
            tool_call_id = call["id"]

            if tool_name not in _TOOL_MAP:
                result = f"Error: Tool '{tool_name}' is not registered."
            else:
                try:
                    tool_instance = _TOOL_MAP[tool_name]
                    await emit_tool_event(tool_name, "start", {"arguments": tool_args})
                    result = await tool_instance.ainvoke(tool_args)
                    await emit_tool_event(tool_name, "finished", {"result": str(result)})
                except Exception as e:
                    logger.error(f"[execute] Tool '{tool_name}' failed: {e}")
                    result = f"Error: Tool execution failed: {e}"

            messages.append(ToolMessage(content=str(result), tool_call_id=tool_call_id))

    current_tool_msgs = [m for m in messages[initial_message_count:] if isinstance(m, ToolMessage)]
    if current_tool_msgs:
        combined_tool_results = "\n\n".join([f"Tool Output:\n{m.content}" for m in current_tool_msgs])
        last_tool_val = current_tool_msgs[-1].content
    else:
        all_tool_msgs = [m for m in messages if isinstance(m, ToolMessage)]
        if all_tool_msgs:
            combined_tool_results = "\n\n".join([f"Tool Output:\n{m.content}" for m in all_tool_msgs])
            last_tool_val = all_tool_msgs[-1].content
        else:
            combined_tool_results = ""
            last_tool_val = ""

    return {
        "messages": messages,
        "tool_results": combined_tool_results,
        "last_route": intent,
        "last_tool_result": last_tool_val,
        "pending_confirmation": pending,
    }