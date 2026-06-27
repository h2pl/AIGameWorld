"""PC decision logic / PC 决策逻辑.

基于 design/04-agent-layer.md §6 / Based on agent layer design.
"""
"""CharacterAgent 子图 / Character Agent Subgraph — compiled StateGraph.

Phase 3: PC/Actor 决策 / PC/Actor decisions.
PC 和 Actor 分别有独立的 compile / PC and Actor have separate compiled graphs.
"""

from typing import TypedDict, Any

from langgraph.graph import StateGraph, END


class PCSubState(TypedDict):
    """PC Agent 子图状态 / PC Agent subgraph state."""
    pc_id: str
    plot_brief: str
    action_out: dict[str, Any] | None


class ActorSubState(TypedDict):
    """Actor Agent 子图状态 / Actor Agent subgraph state."""
    actor_id: str
    plot_brief: str
    action_out: dict[str, Any] | None


def pc_decide_node(state: PCSubState) -> dict:
    """PC 决策 / PC decision.
    
    Mock: 空行动 / Empty action.
    后续 M5 接入 LLM + 记忆检索 / M5: LLM + memory retrieval.
    """
    return {"action_out": None}


def actor_decide_node(state: ActorSubState) -> dict:
    """Actor 决策 / Actor decision.
    
    Mock: 空行动 / Empty action.
    """
    return {"action_out": None}


def build_pc_subgraph() -> StateGraph:
    """构建 PC 子图 / Build PC subgraph."""
    graph = StateGraph(PCSubState)
    graph.add_node("pc_decide", pc_decide_node)
    graph.set_entry_point("pc_decide")
    graph.add_edge("pc_decide", END)
    return graph


def build_actor_subgraph() -> StateGraph:
    """构建 Actor 子图 / Build Actor subgraph."""
    graph = StateGraph(ActorSubState)
    graph.add_node("actor_decide", actor_decide_node)
    graph.set_entry_point("actor_decide")
    graph.add_edge("actor_decide", END)
    return graph


pc_subgraph = build_pc_subgraph().compile()
actor_subgraph = build_actor_subgraph().compile()

