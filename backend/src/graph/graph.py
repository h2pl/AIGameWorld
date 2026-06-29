"""TickGraph 主图 — 7 Phase 顺序执行 + 条件分支。

START
 |
 v
 dm_service.dm_create              [node]      DM 创造情境   dm_create
 |
 v
 world_service.world_update        [node]      World 引擎    world_update
 |
 v
 character_subgraph             [subgraph]  角色决策      character_subgraph
 |
 v
 engine_subgraph                [subgraph]  Engine 路由   engine_subgraph
 |
 v
 state_update_service.state_update [node]      状态合并更新   state_update
 |
 v
 dm_service.dm_narrate             [node]      DM 叙事       dm_narrate
 |
 +-- needs_reflection? --False--> END
 |
 True
 |
 v
 reflection_subgraph [subgraph]  反思/摘要     reflection_subgraph
 |
 v
 END
"""

from langgraph.graph import END, StateGraph

# service（状态适配层）— 模块级导入，方便 key = 文件名.函数名
from ..services import dm_service, state_update_service, world_service
from .state import OverallState

# subgraph（多 node 协调）
from .subgraphs.character_subgraph import character_subgraph
from .subgraphs.engine_subgraph import engine_subgraph
from .subgraphs.reflection_subgraph import reflection_subgraph


def build_tick_graph() -> StateGraph:
    graph = StateGraph(OverallState)

    graph.add_node("dm_service.dm_create", dm_service.dm_create)
    graph.add_node("world_service.world_update", world_service.world_update)
    graph.add_node("character_subgraph", character_subgraph)
    graph.add_node("engine_subgraph", engine_subgraph)
    graph.add_node("state_update_service.state_update", state_update_service.state_update)
    graph.add_node("dm_service.dm_narrate", dm_service.dm_narrate)
    graph.add_node("reflection_subgraph", reflection_subgraph)

    graph.set_entry_point("dm_service.dm_create")
    graph.add_edge("dm_service.dm_create", "world_service.world_update")
    graph.add_edge("world_service.world_update", "character_subgraph")
    graph.add_edge("character_subgraph", "engine_subgraph")
    graph.add_edge("engine_subgraph", "state_update_service.state_update")
    graph.add_edge("state_update_service.state_update", "dm_service.dm_narrate")

    graph.add_conditional_edges(
        "dm_service.dm_narrate",
        lambda s: "reflection_subgraph" if s.get("needs_reflection") else END,
    )
    graph.add_edge("reflection_subgraph", END)

    return graph
