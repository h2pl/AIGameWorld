"""Phase 3 子图: 角色决策 → 交谈 → 探索.

只做 Graph 编排 / Graph orchestration only:
  character_service.decide → talk_service.process → exploration_service.process → END
"""

from langgraph.graph import END, StateGraph

from ...services.character_service import decide
from ...services.exploration_service import process as explore_process
from ...services.talk_service import process as talk_process
from ..state import OverallState


def build_character_subgraph() -> StateGraph:
    """构建角色子图——三个 service 节点 / Three service nodes."""
    graph = StateGraph(OverallState)
    graph.add_node("character_service.decide", decide)
    graph.add_node("talk_service.process", talk_process)
    graph.add_node("exploration_service.process", explore_process)

    graph.set_entry_point("character_service.decide")
    graph.add_edge("character_service.decide", "talk_service.process")
    graph.add_edge("talk_service.process", "exploration_service.process")
    graph.add_edge("exploration_service.process", END)

    return graph


character_subgraph = build_character_subgraph().compile()
