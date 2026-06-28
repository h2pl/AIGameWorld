"""World Engine Subgraph: Phase 2 / 世界引擎子图。

子图以 subgraph-as-node 形式挂入主图, Schema 使用 plain dict;
Node 函数由 nodes/ 层提供, Service 由 engine/ 层提供。
"""
from langgraph.graph import StateGraph, END
from ...nodes.world_nodes import world_update_node


def build_world_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("world_update", world_update_node)
    graph.set_entry_point("world_update")
    graph.add_edge("world_update", END)
    return graph


world_subgraph = build_world_subgraph().compile()
