"""Phase 2 子图: 从 DB 加载 tick 所需状态 + tick 初始化事件构建.

节点顺序：
  load_world → load_scene → load_actors → load_pcs → load_scene_objects
  → assign_pc_positions → build_dm_create_event → build_scene_setup_event
"""

from langgraph.graph import END, StateGraph

from ...services import data_service, tick_init_service
from ..state import OverallState


def build_load_data_subgraph() -> StateGraph:
    """构建数据加载 + tick 初始化子图."""
    graph = StateGraph(OverallState)
    graph.add_node("data.load_world", data_service.load_world)
    graph.add_node("data.load_scene", data_service.load_scene)
    graph.add_node("data.load_actors", data_service.load_actors)
    graph.add_node("data.load_pcs", data_service.load_pcs)
    graph.add_node("data.load_scene_objects", data_service.load_scene_objects)
    graph.add_node("tick_init.init_graph_db", tick_init_service.init_graph_db)
    graph.add_node("tick_init.assign_positions", tick_init_service.assign_pc_positions)
    graph.add_node("tick_init.build_dm_create_event", tick_init_service.build_dm_create_event)
    graph.add_node("tick_init.scene_setup_snapshot", tick_init_service.save_scene_setup_snapshot)

    graph.set_entry_point("data.load_world")
    graph.add_edge("data.load_world", "data.load_scene")
    graph.add_edge("data.load_scene", "data.load_actors")
    graph.add_edge("data.load_actors", "data.load_pcs")
    graph.add_edge("data.load_pcs", "data.load_scene_objects")
    graph.add_edge("data.load_scene_objects", "tick_init.init_graph_db")
    graph.add_edge("tick_init.init_graph_db", "tick_init.assign_positions")
    graph.add_edge("tick_init.assign_positions", "tick_init.build_dm_create_event")
    graph.add_edge("tick_init.build_dm_create_event", "tick_init.scene_setup_snapshot")
    graph.add_edge("tick_init.scene_setup_snapshot", END)

    return graph


load_data_subgraph = build_load_data_subgraph().compile()
