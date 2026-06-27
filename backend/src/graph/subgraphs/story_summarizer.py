"""Story Summarizer Subgraph / 故事摘要子图."""
from langgraph.graph import StateGraph, END
from ...engine.summarizer.summarizer import SummarizerSubState, summarize_node

def build_summarizer_subgraph() -> StateGraph:
    graph = StateGraph(SummarizerSubState)
    graph.add_node("summarize", summarize_node)
    graph.set_entry_point("summarize")
    graph.add_edge("summarize", END)
    return graph

summarizer_subgraph = build_summarizer_subgraph().compile()
