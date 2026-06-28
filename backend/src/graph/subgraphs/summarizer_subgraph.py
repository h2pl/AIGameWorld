"""Story Summarizer Subgraph: Phase 7 / 故事摘要子图。"""
from langgraph.graph import StateGraph, END
from ...nodes.summarizer_nodes import summarizer_node


def build_summarizer_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("summarize", summarizer_node)
    graph.set_entry_point("summarize")
    graph.add_edge("summarize", END)
    return graph


summarizer_subgraph = build_summarizer_subgraph().compile()
