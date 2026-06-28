"""Quest Engine Subgraph: Phase 4 / 任务引擎子图。"""
from langgraph.graph import StateGraph, END
from ...nodes.quest_nodes import quest_node


def build_quest_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("quest_update", quest_node)
    graph.set_entry_point("quest_update")
    graph.add_edge("quest_update", END)
    return graph


quest_subgraph = build_quest_subgraph().compile()
