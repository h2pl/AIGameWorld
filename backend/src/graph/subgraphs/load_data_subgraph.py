"""数据加载子图：从 DB 加载 tick 所需的基础状态 / Load base tick state from DB.

只加载 world + pcs 两个与场景无关的基础状态；场景相关加载（load_scene /
load_actors / load_scene_objects）在主图公共 Phase 进行，因为它们依赖
world.current_scene_id 只是备用记录：load_world 从它恢复进 state，party.decide_scene 每 tick 在 state 内流转，
persist_tick 末尾统一镜像写回（全部持久化都在最后一步）。

节点顺序：
  load_world → load_pcs
"""

from langgraph.graph import END, StateGraph

from ...services import data_service
from ..state import OverallState


def build_load_data_subgraph() -> StateGraph:
    """构建数据加载子图（仅基础状态）."""
    graph = StateGraph(OverallState)
    graph.add_node("data.load_world", data_service.load_world)
    graph.add_node("data.load_pcs", data_service.load_pcs)

    graph.set_entry_point("data.load_world")
    graph.add_edge("data.load_world", "data.load_pcs")
    graph.add_edge("data.load_pcs", END)

    return graph


load_data_subgraph = build_load_data_subgraph().compile()
