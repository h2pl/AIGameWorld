"""Dialogue Engine Subgraph: Phase 4 / 对话引擎子图。"""
from langgraph.graph import StateGraph, END
from ...nodes.dialogue_nodes import dialogue_node


def build_dialogue_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("dialogue_process", dialogue_node)
    graph.set_entry_point("dialogue_process")
    graph.add_edge("dialogue_process", END)
    return graph


dialogue_subgraph = build_dialogue_subgraph().compile()
