"""
Router Node
-----------
Classifies the resolved user intent (from CONV) into a route string
and stores it in state['route'] for downstream nodes.

Reads from state['user_message'] — the context-enriched message produced
by the CONV node — not the raw last message.
"""
import pathlib
import environ
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from agent.llm.load_model import llm
from core.IntentClassifier import get_intent
from core.loadPrompts import LoadPrompts

logger      = logging.getLogger(__name__)
load_prompts = LoadPrompts()

_base = pathlib.Path(__file__).parent.parent.parent
_e    = environ.Env()
_e.read_env(str(_base / ".env"))

AGENT_MODE = _e("AGENT_MODE", default="general")

_SYSTEM_MESSAGES = load_prompts.load_prompt(f"router/{AGENT_MODE}.yaml")

_TEMPLATE = ChatPromptTemplate.from_messages([
    *_SYSTEM_MESSAGES,
    ("human", "{user_message}"),
])

_router_chain = _TEMPLATE | llm


def router(state: dict) -> dict:
    """
    Classify the resolved user intent into a route.
    Reads state['user_message'] (set by CONV node).
    Writes state['route'] for ACT and tool nodes.
    """

    user_message = state.get("user_message") or ""

    if not user_message:
        last = state["messages"][-1]
        user_message = (
            last.content if hasattr(last, "content") else str(last)
        )
        logger.warning("[router] user_message empty — falling back to raw last message")

    response = _router_chain.invoke({"user_message": user_message})
    route    = get_intent(response)

    logger.info(f"[router] '{user_message[:60]}…' → {route!r}")

    return {"route": route}