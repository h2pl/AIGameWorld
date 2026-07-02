"""Phase 3 子图: 角色决策 → 交谈 → 探索.

只做 Graph 编排 / Graph orchestration only:
  character_service.decide → character_service.act → END

场景信息已由 scene_service.build_scene_info 提前构建并注入 state（与谁来用无关，不需要单独节点）/
Scene info is built and injected into state upfront by scene_service.build_scene_info (consumer-independent, no separate node needed).
"""

from langgraph.graph import END, StateGraph

from ...services import character_service
from ..state import OverallState


def build_character_subgraph() -> StateGraph:
    """构建角色子图——两个 service 节点 / Two service nodes."""
    graph = StateGraph(OverallState)
    graph.add_node("character_service.decide", character_service.decide)
    graph.add_node("character_service.act", character_service.act)

    graph.set_entry_point("character_service.decide")
    graph.add_edge("character_service.decide", "character_service.act")
    graph.add_edge("character_service.act", END)

    return graph


character_subgraph = build_character_subgraph().compile()
