"""
Execute Node
------------
Runs the user's request through a LangChain ReAct agent that has access
to ALL MCP-backed tools (math + email).  The final text output is stored
in state['tool_results'] so the summarize node can format it.
"""
import pathlib , logging ,environ
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import AIMessage 
from agent.llm.load_model import llm
from core.loadPrompts import LoadPrompts
from langchain_core.prompts import ChatPromptTemplate , MessagesPlaceholder

load_prompts = LoadPrompts()
logger = logging.getLogger(__name__)

_base = pathlib.Path(__file__).parent.parent.parent
_e = environ.Env()
_e.read_env(str(_base / ".env"))

AGENT_MODE = _e("AGENT_MODE", default="general")
_SYSTEM_PROMPT = load_prompts.load_prompt(f"router/{AGENT_MODE}.yaml")
_TEMPLATE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
 MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
])

agent = create_tool_calling_agent(llm , [] , prompt=_TEMPLATE_PROMPT)
executor = AgentExecutor(agent=agent , tools=[] , verbose=False)

async def execute(state: dict) -> dict:
    """Run the ReAct agent and store the raw output in tool_results."""

    last_message = state["messages"][-1]
    user_text = (
        last_message.content
        if hasattr(last_message, "content")
        else str(last_message)
    )

    # Pass previous messages as chat history (skip the last — it's the input)
    history = state["messages"][:-1]

    result = await executor.ainvoke(
        {
            "input": user_text,
            "chat_history": history,
        }
    )

    raw_output = result.get("output", "")
    logger.info(f"[execute] tool output: {raw_output[:120]}…")

    return {"tool_results": raw_output}