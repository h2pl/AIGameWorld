"""TickGraph 主图 — 7 Phase 顺序执行 + 条件分支。

START
 |
 v
 phase1_dm_create   [node]      DM 创造情境   dm_create_node
 |
 v
 phase2_world       [node]      World 引擎    world_update_node
 |
 v
 phase3_char_decide [subgraph]  角色决策协调   character_coordinator_subgraph
 |
 v
 phase4_engines     [subgraph]  Engine 路由   engine_router_subgraph
 |
 v
 phase5_update      [node]      状态合并更新   state_update_node
 |
 v
 phase6_narrate     [node]      DM 叙事       dm_narrate_node
 |
 +-- needs_reflection? --False--> END
 |
 True
 |
 v
 phase7_reflect     [subgraph]  反思/摘要协调  reflection_coordinator_subgraph
 |
 v
 END
"""

from langgraph.graph import StateGraph, END

from .state import OverallState

# node（单步）
from ..nodes.dm_nodes import dm_create_node, dm_narrate_node
from ..nodes.world_nodes import world_update_node
from ..nodes.state_update_nodes import state_update_node

# subgraph（多 node 协调）
from .subgraphs.character_coordinator_subgraph import character_coordinator_subgraph
from .subgraphs.engine_router_subgraph import engine_router_subgraph
from .subgraphs.reflection_coordinator_subgraph import reflection_coordinator_subgraph


def build_tick_graph() -> StateGraph:
    graph = StateGraph(OverallState)

    graph.add_node("phase1_dm_create", dm_create_node)
    graph.add_node("phase2_world", world_update_node)
    graph.add_node("phase3_char_decide", character_coordinator_subgraph)
    graph.add_node("phase4_engines", engine_router_subgraph)
    graph.add_node("phase5_update", state_update_node)
    graph.add_node("phase6_narrate", dm_narrate_node)
    graph.add_node("phase7_reflect", reflection_coordinator_subgraph)

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
