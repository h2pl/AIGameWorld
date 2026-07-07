"""Phase 2b 子图: tick 初始化逻辑 / tick init subgraph.

当前：
  assign_positions — 为 PC 分配出生点坐标
后续可在此子图内扩展更多 tick 初始化逻辑。
"""

from langgraph.graph import END, StateGraph

from ...services import tick_init_service
from ..state import OverallState


def build_tick_init_subgraph() -> StateGraph:
    """构建 tick 初始化子图."""
    graph = StateGraph(OverallState)
    graph.add_node("tick_init.assign_positions", tick_init_service.assign_pc_positions)

    graph.set_entry_point("tick_init.assign_positions")
    graph.add_edge("tick_init.assign_positions", END)

    return graph


tick_init_subgraph = build_tick_init_subgraph().compile()
