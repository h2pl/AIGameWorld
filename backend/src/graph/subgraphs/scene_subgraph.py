"""Phase 2 子图: 场景信息构建 / Scene info subgraph.

把 scene_service 拆成 7 个节点，按依赖顺序执行：
  build_scene_info → interpret_tilemap → generate_actors → build_actors → build_pcs → generate_scene_objects → build_scene_objects

- interpret_tilemap: 读取 tilemap 文件，LLM 生成语义摘要并写入 scene 表。
- generate_* 节点在当前场景无 NPC/物体时，通过 LLM 动态生成并入库。
"""

from langgraph.graph import END, StateGraph

from ...services import scene_service
from ..state import OverallState


def build_scene_subgraph() -> StateGraph:
    """构建场景子图——7 个 service 节点 / Seven service nodes."""
    graph = StateGraph(OverallState)
    graph.add_node("scene_service.build_scene_info", scene_service.build_scene_info)
    graph.add_node("scene_service.interpret_tilemap", scene_service.interpret_tilemap)
    graph.add_node("scene_service.generate_actors", scene_service.generate_actors)
    graph.add_node("scene_service.build_actors", scene_service.build_actors)
    graph.add_node("scene_service.build_pcs", scene_service.build_pcs)
    graph.add_node("scene_service.generate_scene_objects", scene_service.generate_scene_objects)
    graph.add_node("scene_service.build_scene_objects", scene_service.build_scene_objects)

    graph.set_entry_point("scene_service.build_scene_info")
    graph.add_edge("scene_service.build_scene_info", "scene_service.interpret_tilemap")
    graph.add_edge("scene_service.interpret_tilemap", "scene_service.generate_actors")
    graph.add_edge("scene_service.generate_actors", "scene_service.build_actors")
    graph.add_edge("scene_service.build_actors", "scene_service.build_pcs")
    graph.add_edge("scene_service.build_pcs", "scene_service.generate_scene_objects")
    graph.add_edge("scene_service.generate_scene_objects", "scene_service.build_scene_objects")
    graph.add_edge("scene_service.build_scene_objects", END)

    return graph


scene_subgraph = build_scene_subgraph().compile()
