"""Combat Engine Subgraph: Phase 4 / 战斗引擎子图。"""
from langgraph.graph import StateGraph, END
from ...nodes.combat_nodes import combat_node


def build_combat_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("combat_resolve", combat_node)
    graph.set_entry_point("combat_resolve")
    graph.add_edge("combat_resolve", END)
    return graph


combat_subgraph = build_combat_subgraph().compile()
