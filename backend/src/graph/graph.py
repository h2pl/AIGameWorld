"""TickGraph 主图 — 7 Phase 顺序执行 + 条件分支。

START
 |
 v
 phase1_dm_create   [node]  DM 创造情境   dm_create_node
 |
 v
 phase2_world       [node]  World 引擎    world_update_node
 |
 v
 phase3_char_decide [node]  角色决策协调   phase3_character_decide
 |
 v
 phase4_engines     [node]  Engine 路由   phase4_engine_router
 |
 v
 phase5_update      [node]  状态合并更新   state_update_node
 |
 v
 phase6_narrate     [node]  DM 叙事       dm_narrate_node
 |
 +-- needs_reflection? --False--> END
 |
 True
 |
 v
 phase7_reflect     [node]  反思/摘要协调  phase7_reflection_coordinator
 |
 v
 END
"""

from langgraph.graph import StateGraph, END

from .state import OverallState

from ..nodes.dm_nodes import dm_create_node, dm_narrate_node
from ..nodes.world_nodes import world_update_node
from ..nodes.state_update_nodes import state_update_node
from ..nodes.coordinators import (
    phase3_character_decide,
    phase4_engine_router,
    phase7_reflection_coordinator,
)


def build_tick_graph() -> StateGraph:
    """构建 7 Phase TickGraph — 全部 plain node，零 subgraph。"""
    graph = StateGraph(OverallState)

    graph.add_node("phase1_dm_create", dm_create_node)
    graph.add_node("phase2_world", world_update_node)
    graph.add_node("phase3_char_decide", phase3_character_decide)
    graph.add_node("phase4_engines", phase4_engine_router)
    graph.add_node("phase5_update", state_update_node)
    graph.add_node("phase6_narrate", dm_narrate_node)
    graph.add_node("phase7_reflect", phase7_reflection_coordinator)

    graph.set_entry_point("phase1_dm_create")
    graph.add_edge("phase1_dm_create", "phase2_world")
    graph.add_edge("phase2_world", "phase3_char_decide")
    graph.add_edge("phase3_char_decide", "phase4_engines")
    graph.add_edge("phase4_engines", "phase5_update")
    graph.add_edge("phase5_update", "phase6_narrate")

    graph.add_conditional_edges(
        "phase6_narrate",
        lambda s: "phase7_reflect" if s.get("needs_reflection") else END,
    )
    graph.add_edge("phase7_reflect", END)

    return graph


graph = build_tick_graph().compile()
