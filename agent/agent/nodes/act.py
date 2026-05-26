"""
Execute Node
------------
Runs the user's request through a LangChain ReAct agent.
Injects runtime state variables (route, tool_result, conversation_history)
into the act prompt at invocation time.
"""
import pathlib, logging, environ
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from agent.llm.load_model import llm
from core.loadPrompts import LoadPrompts

load_prompts = LoadPrompts()
logger      = logging.getLogger(__name__)

_base = pathlib.Path(__file__).parent.parent.parent
_e    = environ.Env()
_e.read_env(str(_base / ".env"))

AGENT_MODE = _e("AGENT_MODE", default="general")

_PARTIAL_PROMPT = load_prompts.load_partial_prompt(f"act/{AGENT_MODE}.yaml")

_TEMPLATE_PROMPT = ChatPromptTemplate.from_messages([
    *_PARTIAL_PROMPT.format_prompt(
        route            = "{route}",
        user_message     = "{user_message}",
        tool_result      = "{tool_result}",
        conversation_history = "{conversation_history}",
        last_route       = "{last_route}",
        last_tool_result = "{last_tool_result}",
    ).to_messages(),
    MessagesPlaceholder("chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

agent    = create_tool_calling_agent(llm, [], prompt=_TEMPLATE_PROMPT)
executor = AgentExecutor(agent=agent, tools=[], verbose=False)


async def execute(state: dict) -> dict:
    """Run the ReAct agent with full state context injected into the prompt."""

    last_message = state["messages"][-1]
    user_text    = (
        last_message.content
        if hasattr(last_message, "content")
        else str(last_message)
    )

    history = state["messages"][:-1]

    route             = state.get("route", "CHAT")
    tool_result       = state.get("tool_results", "")
    last_route        = state.get("last_route", "")
    last_tool_result  = state.get("last_tool_result", "")
    conversation_history = "\n".join(
        f"{m.type.upper()}: {m.content}"
        for m in history
        if hasattr(m, "content")
    )

    result = await executor.ainvoke({
        "input"               : user_text,
        "chat_history"        : history,
        "route"               : route,
        "user_message"        : user_text,
        "tool_result"         : tool_result,
        "last_route"          : last_route,
        "last_tool_result"    : last_tool_result,
        "conversation_history": conversation_history,
    })

    raw_output = result.get("output", "")
    logger.info(f"[execute] act output: {raw_output[:120]}…")

    return {
        "tool_results"    : raw_output,
        "last_route"      : route,         
        "last_tool_result": raw_output,
    }