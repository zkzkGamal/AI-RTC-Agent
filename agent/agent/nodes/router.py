"""
Router Node
-----------
Classifies the resolved user intent (from CONV) into a route string:
CONV, PLAN, or DIRECT.
Stores it in state['route'] for downstream nodes.
"""
import logging
from langchain_core.prompts import ChatPromptTemplate
from agent.llm.load_model import llm
from core.loadPrompts import LoadPrompts

logger      = logging.getLogger(__name__)
load_prompts = LoadPrompts()

_SYSTEM_MESSAGES = load_prompts.load_prompt("router/intent_router.yml")

_TEMPLATE = ChatPromptTemplate.from_messages([
    *_SYSTEM_MESSAGES,
    ("human", "{user_message}"),
])

_router_chain = _TEMPLATE | llm


def router(state: dict) -> dict:
    """
    Classify the resolved user intent into a route.
    Reads state['user_message'] (set by CONV node).
    Writes state['route'] for tool execution and planners.
    """
    # If there is a pending confirmation, bypass routing and go DIRECT to executor
    if state.get("pending_confirmation"):
        logger.info("[router] Pending confirmation detected. Bypassing router classification and going DIRECT.")
        return {"route": "DIRECT"}

    user_message = state.get("user_message") or ""

    if not user_message:
        last = state["messages"][-1]
        user_message = (
            last.content if hasattr(last, "content") else str(last)
        )
        logger.warning("[router] user_message empty — falling back to raw last message")

    response = _router_chain.invoke({"user_message": user_message})
    route    = response.content.strip().upper()

    # Normalize output
    if "PLAN" in route:
        route = "PLAN"
    elif "DIRECT" in route:
        route = "DIRECT"
    else:
        route = "CONV"

    logger.info(f"[router] Classified intent as: {route}")
    return {"route": route}