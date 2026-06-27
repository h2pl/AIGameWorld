"""Engine summarizer logic / summarizer 业务逻辑.

基于 design/03-orchestration-layer.md / Based on orchestration layer design.
"""

"""StorySummarizer 子图 / Story Summarizer Subgraph — compiled StateGraph.

Phase 7: 每 N 步压缩 Event Log → 剧情梗概 / Compress events into summary.
"""

from typing import TypedDict, Any

from langgraph.graph import StateGraph, END


class SummarizerSubState(TypedDict):
    """摘要器子图状态 / Summarizer subgraph state."""
    events: list[dict[str, Any]]
    tick: int
    summary: str


def summarize_node(state: SummarizerSubState) -> dict:
    """压缩事件 / Compress events.
    
    Mock: 空摘要 / Empty summary.
    """
    return {"summary": ""}


def build_summarizer_subgraph() -> StateGraph:
    """构建 Summarizer 子图 / Build Summarizer subgraph."""
    graph = StateGraph(SummarizerSubState)
    graph.add_node("summarize", summarize_node)
    graph.set_entry_point("summarize")
    graph.add_edge("summarize", END)
    return graph


summarizer_subgraph = build_summarizer_subgraph().compile()
