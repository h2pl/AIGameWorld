"""DM Subgraphs: Phase 1 create + Phase 6 narrate / DM 子图。

子图以 subgraph-as-node 形式挂入主图, Schema 使用 plain dict;
Node 函数由 nodes/ 层提供, Service 由 engine/ 层提供。
"""
from langgraph.graph import StateGraph, END
from ...nodes.dm_nodes import dm_create_node, dm_narrate_node


def build_dm_create_subgraph() -> StateGraph:
    """Phase 1: DM 创造情境 / DM creates context."""
    graph = StateGraph(dict)
    graph.add_node("dm_create", dm_create_node)
    graph.set_entry_point("dm_create")
    graph.add_edge("dm_create", END)
    return graph


def build_dm_narrate_subgraph() -> StateGraph:
    """Phase 6: DM 叙事 / DM narrates."""
    graph = StateGraph(dict)
    graph.add_node("dm_narrate", dm_narrate_node)
    graph.set_entry_point("dm_narrate")
    graph.add_edge("dm_narrate", END)
    return graph


dm_create_subgraph = build_dm_create_subgraph().compile()
dm_narrate_subgraph = build_dm_narrate_subgraph().compile()
