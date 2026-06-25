"""
AI Agent Graph Definition (agent.py)
------------------------------------
Wires up all nodes using LangGraph StateGraph.
Flow:
             ┌──────────┐
             │  Router  │
             └────┬─────┘
                  │ Conditional Route
        ┌─────────┼─────────┐
        ▼         ▼         ▼
    ┌───────┐ ┌───────┐ ┌────────┐
    │ CONV  │ │ PLAN  │ │ DIRECT │
    └───┬───┘ └───┬───┘ └───┬────┘
        │         ▼         │
        │     ┌───────┐     │
        │     │Planner│     │
        │     └───┬───┘     │
        │         └────┬────┘
        │              ▼
        │         ┌─────────┐
        │         │Executor │ (Human-In-The-Loop check)
        │         └────┬────┘
        │              │ Conditional (If HIL pending -> END, else continue)
        ▼              ▼
    ┌───────────────────────┐
    │     Conversation      │ (Actor synthesis)
    └──────────┬────────────┘
               ▼
             [END]
"""
import os
import pathlib
import sys
from langgraph.graph import StateGraph, END

project_root = pathlib.Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root.parent))
sys.path.insert(0, str(project_root))

from agent.agent.state import AgentState
from agent.agent.nodes.router import router as router_node
from agent.agent.nodes.planner import planner as planner_node
from agent.agent.nodes.act import execute as execute_node
from agent.agent.nodes.conversation import conversation as conversation_node


def route_after_router(state: AgentState) -> str:
    route = state.get("route", "CONV")
    if route == "PLAN":
        return "planner"
    elif route == "DIRECT":
        return "executor"
    else:
        return "conversation"

def route_after_planner(state: AgentState) -> str:
    if state.get("skip_tools"):
        return "conversation"
    return "executor"

def route_after_executor(state: AgentState) -> str:
    if state.get("pending_confirmation"):
        return END
    return "conversation"

workflow = StateGraph(AgentState)

workflow.add_node("router", router_node)
workflow.add_node("planner", planner_node)
workflow.add_node("executor", execute_node)
workflow.add_node("conversation", conversation_node)

workflow.set_entry_point("router")

workflow.add_conditional_edges(
    "router",
    route_after_router,
    {
        "planner": "planner",
        "executor": "executor",
        "conversation": "conversation",
    }
)

workflow.add_conditional_edges(
    "planner",
    route_after_planner,
    {
        "executor": "executor",
        "conversation": "conversation",
    }
)

workflow.add_conditional_edges(
    "executor",
    route_after_executor,
    {
        END: END,
        "conversation": "conversation",
    }
)

workflow.add_edge("conversation", END)

graph = workflow.compile()

try:
    image_bytes = graph.get_graph().draw_mermaid_png()
    output_path = project_root / "agent_graph.png"
    with open(output_path, "wb") as f:
        f.write(image_bytes)
    logger_msg = f"Successfully saved agent graph visualization to: {output_path}"
    print(logger_msg)
except Exception as e:
    print(f"Could not generate agent graph visualization image: {e}")