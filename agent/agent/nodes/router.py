"""
Router Node
-----------
This node uses a simple LLM prompt to determine the user's intent based on the content of their message. 
The classified intent is stored in the state for downstream nodes to use in routing the conversation appropriately.
"""
import pathlib , environ , logging
from agent.llm.load_model import llm
from core.IntentClassifier import get_intent
from core.loadPrompts import LoadPrompts
from langchain_core.messages import SystemMessage, HumanMessage



load_prompts = LoadPrompts()


logger = logging.getLogger(__name__)

_base = pathlib.Path(__file__).parent.parent.parent
_e = environ.Env()
_e.read_env(str(_base / ".env"))

AGENT_MODE = _e("AGENT_MODE", default="general")
_SYSTEM_PROMPT = load_prompts.load_prompt(f"router/{AGENT_MODE}.yaml")



def router(state: dict) -> dict:
    """Classify intent and store it in state['intent']."""

    last_message = state["messages"][-1]
    # Extract text whether it's a BaseMessage or a plain string
    user_text = (
        last_message.content
        if hasattr(last_message, "content")
        else str(last_message)
    )

    response = llm.invoke(
        [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=user_text),
        ]
    )
    intent = get_intent(response)
    logger.info(f"[router] intent classified as: {intent!r}")
    return {"intent": intent}