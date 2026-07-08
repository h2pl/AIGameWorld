"""Phase 2b 子图: tick 初始化逻辑 / tick init subgraph.

当前：
  assign_positions         → 为 PC 分配出生点坐标
  build_dm_create_event    → 构建 dm_create 事件（tick 第一个事件）
  build_scene_setup_event  → 构建 scene_setup 事件（PC 坐标为起始坐标，未被 action 更新）
后续可在此子图内扩展更多 tick 初始化逻辑。
"""

from langgraph.graph import END, StateGraph

from ...services import tick_init_service
from ..state import OverallState


def build_tick_init_subgraph() -> StateGraph:
    """构建 tick 初始化子图."""
    graph = StateGraph(OverallState)
    graph.add_node("tick_init.assign_positions", tick_init_service.assign_pc_positions)
    graph.add_node("tick_init.dm_create_event", tick_init_service.build_dm_create_event)
    graph.add_node("tick_init.scene_setup_event", tick_init_service.build_scene_setup_event)

    graph.set_entry_point("tick_init.assign_positions")
    graph.add_edge("tick_init.assign_positions", "tick_init.dm_create_event")
    graph.add_edge("tick_init.dm_create_event", "tick_init.scene_setup_event")
    graph.add_edge("tick_init.scene_setup_event", END)

    return graph


tick_init_subgraph = build_tick_init_subgraph().compile()
