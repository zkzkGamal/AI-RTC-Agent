"""
Conversation Node
-----------------
Resolves the user's latest message into a clean, context-enriched intent
by injecting full conversation history and cross-turn memory into the CONV
prompt. The output is stored in state['user_message'] and passed to the
ROUTER node — it is NOT a user-facing reply.
"""
import pathlib
import logging
import environ
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from agent.llm.load_model import llm
from core.loadPrompts import LoadPrompts

logger = logging.getLogger(__name__)

_base = pathlib.Path(__file__).parent.parent.parent
_e = environ.Env()
_e.read_env(str(_base / ".env"))

load_prompts = LoadPrompts()
AGENT_MODE   = _e("AGENT_MODE", default="general")

_PARTIAL_PROMPT = load_prompts.load_partial_prompt(f"conv/{AGENT_MODE}.yaml")

_TEMPLATE = ChatPromptTemplate.from_messages([
    *_PARTIAL_PROMPT.format_prompt(
        user_message         = "{user_message}",
        conversation_history = "{conversation_history}",
        last_route           = "{last_route}",
        last_tool_result     = "{last_tool_result}",
    ).to_messages(),
    ("human", "{user_message}"),
])

_conv_chain = _TEMPLATE | llm


def conversation(state: dict) -> dict:
    """
    Resolve the user's latest message using full conversation context.
    Writes the resolved intent to state['user_message'] for the router.
    """

    last_message = state["messages"][-1]
    raw_input    = (
        last_message.content
        if hasattr(last_message, "content")
        else str(last_message)
    )

    prior_messages = state["messages"][:-1]
    conversation_history = "\n".join(
        f"{m.type.upper()}: {m.content}"
        for m in prior_messages
        if hasattr(m, "content")
    ) or "No prior conversation."

    last_route       = state.get("last_route", "") or ""
    last_tool_result = state.get("last_tool_result", "") or ""

    response = _conv_chain.invoke({
        "user_message"        : raw_input,
        "conversation_history": conversation_history,
        "last_route"          : last_route,
        "last_tool_result"    : last_tool_result,
    })

    resolved_message = response.content.strip()
    logger.info(f"[conv] raw='{raw_input[:60]}…' → resolved='{resolved_message[:60]}…'")

    return {"user_message": resolved_message}