"""Exploration Engine Subgraph: Phase 4 / 探索引擎子图。"""
from langgraph.graph import StateGraph, END
from ...nodes.exploration_nodes import exploration_node


def build_exploration_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("exploration_process", exploration_node)
    graph.set_entry_point("exploration_process")
    graph.add_edge("exploration_process", END)
    return graph


exploration_subgraph = build_exploration_subgraph().compile()
