"""Phase 7 协调子图: Reflection + Summarizer / 反思 + 摘要协调子图。"""
from typing import Any

from langgraph.graph import StateGraph, END

from .reflection_subgraph import reflection_subgraph
from .summarizer_subgraph import summarizer_subgraph


def _reflection_coordinator_node(state: dict[str, Any]) -> dict[str, Any]:
    """协调 Reflection + Summarizer / Coordinate reflection and summarizer."""
    reflection_subgraph.invoke({"character_id": "", "memories": []})
    summarizer_subgraph.invoke({"events": [], "tick": state.get("tick", 0)})
    return {"reflected_characters": [], "summary_compressed": False}


def build_reflection_coordinator_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("reflection_coordinator", _reflection_coordinator_node)
    graph.set_entry_point("reflection_coordinator")
    graph.add_edge("reflection_coordinator", END)
    return graph


reflection_coordinator_subgraph = build_reflection_coordinator_subgraph().compile()
