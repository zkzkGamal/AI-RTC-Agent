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

# Setup paths for local package resolution
project_root = pathlib.Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root.parent))
sys.path.insert(0, str(project_root))

from agent.agent.state import AgentState
from agent.agent.nodes.router import router as router_node
from agent.agent.nodes.planner import planner as planner_node
from agent.agent.nodes.act import execute as execute_node
from agent.agent.nodes.conversation import conversation as conversation_node


# Define routing conditional paths
def route_after_router(state: AgentState) -> str:
    route = state.get("route", "CONV")
    if route == "PLAN":
        return "planner"
    elif route == "DIRECT":
        return "executor"
    else:
        return "conversation"

# Define execution conditional paths (HIL check)
def route_after_executor(state: AgentState) -> str:
    # If a dangerous tool is pending confirmation, halt the graph execution
    if state.get("pending_confirmation"):
        return END
    return "conversation"

# 1. Build the StateGraph
workflow = StateGraph(AgentState)

# 2. Add all Nodes
workflow.add_node("router", router_node)
workflow.add_node("planner", planner_node)
workflow.add_node("executor", execute_node)
workflow.add_node("conversation", conversation_node)

# 3. Add Edges & Conditional Routing
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

workflow.add_edge("planner", "executor")

workflow.add_conditional_edges(
    "executor",
    route_after_executor,
    {
        END: END,
        "conversation": "conversation",
    }
)

workflow.add_edge("conversation", END)

# 4. Compile the Graph
graph = workflow.compile()

# 5. Export Graph Image Visualization
try:
    image_bytes = graph.get_graph().draw_mermaid_png()
    output_path = project_root / "agent_graph.png"
    with open(output_path, "wb") as f:
        f.write(image_bytes)
    logger_msg = f"Successfully saved agent graph visualization to: {output_path}"
    print(logger_msg)
except Exception as e:
    print(f"Could not generate agent graph visualization image: {e}")