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
from core.IntentClassifier import AGENT_MODE, get_intent

logger      = logging.getLogger(__name__)
load_prompts = LoadPrompts()

# Flow intent router system messages (CONV, DIRECT, PLAN)
_SYSTEM_MESSAGES = load_prompts.load_prompt("router/intent_router.yml")
_TEMPLATE = ChatPromptTemplate.from_messages([
    *_SYSTEM_MESSAGES,
    ("human", "{user_message}"),
])
_router_chain = _TEMPLATE | llm

# Business intent router system messages (CHAT, RECRUITMENT, EMAIL, etc.)
_BUSINESS_SYSTEM_MESSAGES = load_prompts.load_prompt(f"router/{AGENT_MODE}.yaml")
_business_template = ChatPromptTemplate.from_messages([
    *_BUSINESS_SYSTEM_MESSAGES,
    ("human", "{user_message}"),
])
_business_router_chain = _business_template | llm


def router(state: dict) -> dict:
    """
    Classify the resolved user intent into a route.
    Reads state['user_message'] (set by CONV node).
    Writes state['route'] for tool execution and planners.
    Writes state['intent'] for prompt synthesis and behaviors.
    """
    # If there is a pending confirmation, bypass routing and go DIRECT to executor
    if state.get("pending_confirmation"):
        logger.info("[router] Pending confirmation detected. Bypassing router classification and going DIRECT.")
        intent = state.get("intent") or "CHAT"
        return {"route": "DIRECT", "intent": intent}

    user_message = state.get("user_message") or ""

    if not user_message:
        last = state["messages"][-1]
        user_message = (
            last.content if hasattr(last, "content") else str(last)
        )
        logger.warning("[router] user_message empty — falling back to raw last message")

    # 1. Classify execution flow route (CONV, DIRECT, PLAN)
    response = _router_chain.invoke({"user_message": user_message})
    route    = response.content.strip().upper()

    # Normalize output
    if "PLAN" in route:
        route = "PLAN"
    elif "DIRECT" in route:
        route = "DIRECT"
    else:
        route = "CONV"

    # 2. Classify domain business intent (CHAT, RECRUITMENT, PAYROLL, etc. / WEB_SEARCH, EMAIL, etc.)
    # Optimization: Conversational flow routes default to CHAT intent without an extra LLM call
    if route == "CONV":
        intent = "CHAT"
    else:
        bus_response = _business_router_chain.invoke({"user_message": user_message})
        intent = get_intent(bus_response)

    logger.info(f"[router] Classified intent as: {route} | Business intent: {intent}")
    return {"route": route, "intent": intent}