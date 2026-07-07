"""Phase 2 子图: 场景信息构建 / Scene info subgraph.

把 scene_service 拆成 4 个节点，按依赖顺序执行：
  build_scene_info → build_actors → build_pcs → build_scene_objects
"""

from langgraph.graph import END, StateGraph

from ...services import scene_service
from ..state import OverallState


def build_scene_subgraph() -> StateGraph:
    """构建场景子图——4 个 service 节点 / Four service nodes."""
    graph = StateGraph(OverallState)
    graph.add_node("scene_service.build_scene_info", scene_service.build_scene_info)
    graph.add_node("scene_service.build_actors", scene_service.build_actors)
    graph.add_node("scene_service.build_pcs", scene_service.build_pcs)
    graph.add_node("scene_service.build_scene_objects", scene_service.build_scene_objects)

    graph.set_entry_point("scene_service.build_scene_info")
    graph.add_edge("scene_service.build_scene_info", "scene_service.build_actors")
    graph.add_edge("scene_service.build_actors", "scene_service.build_pcs")
    graph.add_edge("scene_service.build_pcs", "scene_service.build_scene_objects")
    graph.add_edge("scene_service.build_scene_objects", END)

    return graph


scene_subgraph = build_scene_subgraph().compile()
