"""DM Subgraphs: create + narrate 两个独立子图 / Two separate DM subgraphs.

Phase 1 调用 dm_create_subgraph, Phase 6 调用 dm_narrate_subgraph.
单入口+条件路由无法区分两个 Phase 的语义, 改为两个独立子图.
"""
from langgraph.graph import StateGraph, END

from ...engine.dm.dm import (
    DMSubState, dm_create_node, dm_narrate_node,
)


def build_dm_create_subgraph() -> StateGraph:
    """Phase 1: DM 创造情境 / DM creates context."""
    graph = StateGraph(DMSubState)
    graph.add_node("dm_create", dm_create_node)
    graph.set_entry_point("dm_create")
    graph.add_edge("dm_create", END)
    return graph


def build_dm_narrate_subgraph() -> StateGraph:
    """Phase 6: DM 叙事 / DM narrates."""
    graph = StateGraph(DMSubState)
    graph.add_node("dm_narrate", dm_narrate_node)
    graph.set_entry_point("dm_narrate")
    graph.add_edge("dm_narrate", END)
    return graph


dm_create_subgraph = build_dm_create_subgraph().compile()
dm_narrate_subgraph = build_dm_narrate_subgraph().compile()
