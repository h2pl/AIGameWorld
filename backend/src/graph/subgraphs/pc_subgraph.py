"""Phase 3 子图: 角色决策 → 交谈 → 探索.

只做 Graph 编排 / Graph orchestration only:
  pc_service.decide → pc_service.act → END

场景信息已由 scene_service.build_scene_info 提前构建并注入 state（与谁来用无关，不需要单独节点）/
Scene info is built and injected into state upfront by scene_service.build_scene_info (consumer-independent, no separate node needed).
"""

from langgraph.graph import END, StateGraph

from ...services import pc_service
from ..state import OverallState


def build_pc_subgraph() -> StateGraph:
    """构建角色子图——两个 service 节点 / Two service nodes."""
    graph = StateGraph(OverallState)
    graph.add_node("pc_service.decide", pc_service.decide)
    graph.add_node("pc_service.act", pc_service.act)

    graph.set_entry_point("pc_service.decide")
    graph.add_edge("pc_service.decide", "pc_service.act")
    graph.add_edge("pc_service.act", END)

    return graph


pc_subgraph = build_pc_subgraph().compile()
