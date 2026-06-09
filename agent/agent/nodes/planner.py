"""
Planner Node
------------
Generates a step-by-step execution plan for complex requests.
Stores the plan in state['plan'] for downstream execution.
"""
import logging
from langchain_core.prompts import ChatPromptTemplate
from agent.llm.load_model import llm
from core.loadPrompts import LoadPrompts

logger      = logging.getLogger(__name__)
load_prompts = LoadPrompts()

_PARTIAL_PROMPT = load_prompts.load_partial_prompt("plan/planner.yml")

_TEMPLATE = ChatPromptTemplate.from_messages([
    *_PARTIAL_PROMPT.format_prompt(
        user_message = "{user_message}",
    ).to_messages(),
    ("human", "{user_message}"),
])

_planner_chain = _TEMPLATE | llm


def planner(state: dict) -> dict:
    """
    Generate an execution plan.
    Reads state['user_message'] (resolved intent).
    Writes state['plan'].
    """
    user_message = state.get("user_message") or ""

    if not user_message:
        last = state["messages"][-1]
        user_message = (
            last.content if hasattr(last, "content") else str(last)
        )

    logger.info(f"[planner] Generating plan for user request: {user_message[:60]}...")
    response = _planner_chain.invoke({"user_message": user_message})
    plan = response.content.strip()

    logger.info(f"[planner] Generated plan:\n{plan}")
    return {"plan": plan}
