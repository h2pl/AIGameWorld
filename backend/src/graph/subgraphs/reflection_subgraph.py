"""Reflection subgraph compatibility wrapper / 反思子图兼容包装。"""

from langgraph.graph import END, StateGraph

from ...services import reflection_service
from ..state import ReflectionSubState


def build_reflection_subgraph() -> StateGraph:
    """Build single-node reflection subgraph / 构建单节点反思子图。"""
    graph = StateGraph(ReflectionSubState)
    graph.add_node("reflection_service.reflect", reflection_service.reflect)
    graph.set_entry_point("reflection_service.reflect")
    graph.add_edge("reflection_service.reflect", END)
    return graph


reflection_subgraph = build_reflection_subgraph().compile()
