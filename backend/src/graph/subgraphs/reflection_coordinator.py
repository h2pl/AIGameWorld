"""Phase 7 协调子图: Reflection + Summarizer。"""
from typing import Any

from langgraph.graph import StateGraph, END

from ...nodes.reflection_nodes import reflection_node
from ...nodes.summarizer_nodes import summarizer_node


def _reflection_coordinator(state: dict[str, Any]) -> dict[str, Any]:
    """协调 Reflection + Summarizer。"""
    reflection_node({"character_id": "", "memories": []})
    summarizer_node({"events": [], "tick": state.get("tick", 0)})
    return {"reflected_characters": [], "summary_compressed": False}


def build_reflection_coordinator_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("reflection_coordinator", _reflection_coordinator)
    graph.set_entry_point("reflection_coordinator")
    graph.add_edge("reflection_coordinator", END)
    return graph


reflection_coordinator_subgraph = build_reflection_coordinator_subgraph().compile()
