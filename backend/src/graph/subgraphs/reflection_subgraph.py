"""Phase 7 子图: Reflection + Summarizer。

┌── entry ──┐
│  reflect   │  角色反思 → reflected_characters
│ summarize  │  事件压缩 → summary_compressed
└─── END ────┘
"""

from langgraph.graph import END, StateGraph

from ...services import reflection_service, summarizer_service
from ..state import ReflectionSubState


def build_reflection_subgraph() -> StateGraph:
    graph = StateGraph(ReflectionSubState)
    graph.add_node("reflection_service.reflect", reflection_service.reflect)
    graph.add_node("summarizer_service.summarize", summarizer_service.summarize)
    graph.set_entry_point("reflection_service.reflect")
    graph.add_edge("reflection_service.reflect", "summarizer_service.summarize")
    graph.add_edge("summarizer_service.summarize", END)
    return graph


reflection_subgraph = build_reflection_subgraph().compile()
