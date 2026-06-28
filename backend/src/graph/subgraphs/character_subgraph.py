"""Phase 3 子图: 唤醒 PC + Actor 决策。"""
from langgraph.graph import StateGraph, END
from ...nodes.character_decide_node import character_decide_node


def build_character_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("character_decide", character_decide_node)
    graph.set_entry_point("character_decide")
    graph.add_edge("character_decide", END)
    return graph


character_subgraph = build_character_subgraph().compile()
