"""Phase 3 子图: 角色决策 → 交谈 → 探索.

只做 Graph 编排 / Graph orchestration only:
  character_service.perceive → character_service.decide → character_service.act → END
"""

from langgraph.graph import END, StateGraph

from ...services import character_service
from ..state import OverallState


def build_character_subgraph() -> StateGraph:
    """构建角色子图——三个 service 节点 / Three service nodes."""
    graph = StateGraph(OverallState)
    graph.add_node("character_service.perceive", character_service.perceive)
    graph.add_node("character_service.decide", character_service.decide)
    graph.add_node("character_service.act", character_service.act)

    graph.set_entry_point("character_service.perceive")
    graph.add_edge("character_service.perceive", "character_service.decide")
    graph.add_edge("character_service.decide", "character_service.act")
    graph.add_edge("character_service.act", END)

    return graph


character_subgraph = build_character_subgraph().compile()
