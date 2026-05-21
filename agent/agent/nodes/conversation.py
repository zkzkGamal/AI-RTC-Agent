"""
Conversation Node
-----------------
Handles general chitchat and knowledge questions — no tool calls.
Passes the full message history to the LLM and appends its reply.
"""
import pathlib
import logging
import environ
from langchain_core.messages import SystemMessage, AIMessage
from agent.llm.load_model import llm
from core.loadPrompts import LoadPrompts

logger = logging.getLogger(__name__)

_base = pathlib.Path(__file__).parent.parent.parent
_e = environ.Env()
_e.read_env(str(_base / ".env"))
load_prompts = LoadPrompts()

AGENT_MODE = _e("AGENT_MODE", default="general")
_SYSTEM_PROMPT = load_prompts.load_prompt(f"router/{AGENT_MODE}.yaml")
_SYSTEM = SystemMessage(content=_SYSTEM_PROMPT)



def conversation(state: dict) -> dict:
    """Generate a conversational reply and append it to messages."""

    messages_with_sys = [_SYSTEM] + list(state["messages"])
    response = llm.invoke(messages_with_sys)

    ai_msg = AIMessage(content=response.content)
    logger.info(f"[conversation] reply: {response.content[:20]}…")

    return {"messages": state["messages"] + [ai_msg]}