"""
This module defines the AgentState TypedDict, which represents the state of the agent during its interactions.
The AgentState includes the message history, the classified intent category, any pending confirmations for tool calls,
a log of tool calls made, and the results from those tool calls. 
This structured state allows the agent to maintain context and manage its interactions effectively across different nodes in the conversation flow.
"""

from typing import Annotated, Sequence, Dict, Optional , List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    category: Optional[List]
    pending_confirmation: Optional[Dict[str, Optional[str]]]
    tool_calls: Optional[List[Dict[str, str]]]
    tool_results: Optional[str]
