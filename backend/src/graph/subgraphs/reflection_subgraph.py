"""Phase 7 子图: Reflection + Summarizer。"""
from typing import Any

from langgraph.graph import StateGraph, END

from ...nodes.reflection_nodes import reflection_node
from ...nodes.summarizer_nodes import summarizer_node


def _reflection_decide(state: dict[str, Any]) -> dict[str, Any]:
    """协调 Reflection + Summarizer。"""
    reflection_node({"character_id": "", "memories": []})
    summarizer_node({"events": [], "tick": state.get("tick", 0)})
    return {"reflected_characters": [], "summary_compressed": False}


def build_reflection_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("reflection_decide", _reflection_decide)
    graph.set_entry_point("reflection_decide")
    graph.add_edge("reflection_decide", END)
    return graph


reflection_subgraph = build_reflection_subgraph().compile()
