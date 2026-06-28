"""Phase 7 子图: Reflection + Summarizer。"""
from langgraph.graph import StateGraph, END
from ...nodes.reflection_decide import reflection_decide_node


def build_reflection_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("reflection_decide", reflection_decide_node)
    graph.set_entry_point("reflection_decide")
    graph.add_edge("reflection_decide", END)
    return graph


reflection_subgraph = build_reflection_subgraph().compile()
