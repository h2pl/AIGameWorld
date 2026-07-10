"""Reflection subgraph compatibility wrapper / 反思子图兼容包装。"""

from langgraph.graph import END, StateGraph

from ...services import reflection_service
from ..state import ReflectionSubState


def build_reflection_subgraph() -> StateGraph:
    """Build single-node reflection subgraph / 构建单节点反思子图。(已迁移至 Scheduler 异步处理)"""
    graph = StateGraph(ReflectionSubState)
    
    def _noop(state: ReflectionSubState) -> dict:
        return {"reflected_pcs": []}
        
    graph.add_node("noop", _noop)
    graph.set_entry_point("noop")
    graph.add_edge("noop", END)
    return graph


reflection_subgraph = build_reflection_subgraph().compile()
