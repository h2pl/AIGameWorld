"""Phase 2a 子图: 从 DB 加载 tick 所需状态 / Load tick state from DB.

4 个 data_service 节点按依赖顺序执行：
  load_scene → load_actors → load_pcs → load_scene_objects
"""

from langgraph.graph import END, StateGraph

from ...services import data_service
from ..state import OverallState


def build_load_data_subgraph() -> StateGraph:
    """构建数据加载子图——4 个 DB 节点 / Four DB nodes."""
    graph = StateGraph(OverallState)
    graph.add_node("data.load_scene", data_service.load_scene)
    graph.add_node("data.load_actors", data_service.load_actors)
    graph.add_node("data.load_pcs", data_service.load_pcs)
    graph.add_node("data.load_scene_objects", data_service.load_scene_objects)

    graph.set_entry_point("data.load_scene")
    graph.add_edge("data.load_scene", "data.load_actors")
    graph.add_edge("data.load_actors", "data.load_pcs")
    graph.add_edge("data.load_pcs", "data.load_scene_objects")
    graph.add_edge("data.load_scene_objects", END)

    return graph


load_data_subgraph = build_load_data_subgraph().compile()
