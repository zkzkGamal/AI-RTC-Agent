"""
Conversation Node (conversation.py)
-----------------------------------
Acts as the final user-facing response generator.
- If route is CONV -> Generates a direct conversational response using conversation prompts.
- If route is PLAN or DIRECT -> Synthesizes tool results and plans into a final user response.
"""
import pathlib
import logging
import environ
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from agent.llm.load_model import llm
from core.loadPrompts import LoadPrompts

logger = logging.getLogger(__name__)
load_prompts = LoadPrompts()

_base = pathlib.Path(__file__).parent.parent.parent
_e    = environ.Env()
_e.read_env(str(_base / ".env"))

AGENT_MODE = _e("AGENT_MODE", default="general")

# Load prompt templates
_CONV_PARTIAL = load_prompts.load_partial_prompt(f"conversations/{AGENT_MODE}.yaml")
_ACT_PARTIAL  = load_prompts.load_partial_prompt(f"act/{AGENT_MODE}.yaml")

# Define Chat Chains
_CONV_TEMPLATE = ChatPromptTemplate.from_messages([
    *_CONV_PARTIAL.format_prompt(
        user_message         = "{user_message}",
        conversation_history = "{conversation_history}",
        last_route           = "{last_route}",
        last_tool_result     = "{last_tool_result}",
    ).to_messages(),
    ("human", "{user_message}"),
])
_conv_chain = _CONV_TEMPLATE | llm

_ACT_TEMPLATE = ChatPromptTemplate.from_messages([
    *_ACT_PARTIAL.format_prompt(
        route        = "{route}",
        user_message = "{user_message}",
        tool_result  = "{tool_result}",
    ).to_messages(),
    ("human", "{user_message}"),
])
_act_chain = _ACT_TEMPLATE | llm


def conversation(state: dict) -> dict:
    """
    Format the final response for the user.
    Appends the final AIMessage to state['messages'].
    """
    messages = list(state.get("messages", []))
    route = state.get("route", "CONV")
    intent = state.get("intent", "CHAT")
    plan = state.get("plan", "")
    tool_results = state.get("tool_results", "")

    # Static metadata from prompts config
    name = load_prompts._static.get("name", "")
    home = load_prompts._static.get("home", "")

    user_text = messages[-1].content if messages else ""
    history = messages[:-1]
    conversation_history = "\n".join(
        f"{m.type.upper()}: {m.content}"
        for m in history
        if hasattr(m, "content")
    ) or "No prior conversation."

    last_route = state.get("last_route", "")
    last_tool_result = state.get("last_tool_result", "")

    if route == "CONV":
        logger.info("[conversation] Processing direct conversation...")
        response = _conv_chain.invoke({
            "name": name,
            "home": home,
            "user_message": user_text,
            "conversation_history": conversation_history,
            "last_route": last_route,
            "last_tool_result": last_tool_result,
        })
    else:
        logger.info(f"[conversation] Synthesizing tool outputs for intent: {intent}")
        # If there is a plan, prepend it to the tool results for the actor synthesis
        combined_results = f"Plan:\n{plan}\n\nExecution Results:\n{tool_results}" if plan else tool_results
        response = _act_chain.invoke({
            "name": name,
            "home": home,
            "route": intent,
            "user_message": user_text,
            "tool_result": combined_results,
        })

    final_message = response.content.strip()

    # Clean up "Resolved Message:" prefix and surrounding quotes
    import re
    cleaned = final_message
    cleaned = re.sub(r'^(?:\*\*|)?Resolved\s+Message(?:\*\*|)?:\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()
    final_message = cleaned

    logger.info(f"[conversation] Final output generated: {final_message[:120]}...")

    # Return state updates
    return {
        "messages": [AIMessage(content=final_message)],
        "user_message": user_text,
    }