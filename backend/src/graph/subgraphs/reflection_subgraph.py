"""Reflection Subgraph: Phase 7 / 角色反思子图。"""
from langgraph.graph import StateGraph, END
from ...nodes.reflection_nodes import reflection_node


def build_reflection_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("reflect", reflection_node)
    graph.set_entry_point("reflect")
    graph.add_edge("reflect", END)
    return graph


reflection_subgraph = build_reflection_subgraph().compile()
