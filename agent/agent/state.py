"""
AgentState defines the full shared state passed between all nodes in the 
multi-agent ReAct pipeline:

  CONV → ROUTER → TOOL NODES → ACT

Each field maps to a specific stage of the pipeline:
  - messages              : full conversation history (auto-merged by add_messages)
  - user_message          : resolved message from CONV, passed to ROUTER and ACT
  - route                 : classification from ROUTER (e.g. CHAT, EMAIL, CALENDAR)
  - tool_calls            : structured tool invocations requested by the agent
  - tool_results          : raw output returned by the tool node
  - last_route            : route from the previous turn (used by CONV for context)
  - last_tool_result      : tool output from the previous turn (used by CONV for context)
  - error                 : error message if any node fails, for graceful fallback
This structured state allows for clear data flow and context sharing across the entire agent pipeline, enabling more
  coherent and informed decision-making by the agent.
"""

from typing import Annotated, Sequence, Dict, Optional, List, Any
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_message: Optional[str]

    route: Optional[str]
    intent: Optional[str]

    tool_calls: Optional[List[Dict[str, str]]]
    tool_results: Optional[str]

    last_route: Optional[str]
    last_tool_result: Optional[str]

    pending_confirmation: Optional[Dict[str, Any]]
    plan: Optional[str]

    error: Optional[str]

