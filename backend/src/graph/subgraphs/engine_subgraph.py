"""Phase 4 子图: 路由到各 Engine。"""
from langgraph.graph import StateGraph, END
from ...nodes.engine_route_node import engine_route_node


def build_engine_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("engine_route", engine_route_node)
    graph.set_entry_point("engine_route")
    graph.add_edge("engine_route", END)
    return graph


engine_subgraph = build_engine_subgraph().compile()
