"""TickGraph 主图 — Phase 顺序执行 + 条件分支.

START
 |
 v
 message_service.create_message     [node]      创建消息       create_message
 |
 v
 dm_service.dm_create              [node]      DM 创造情境   dm_create
 |
 v
 scene_service.process_scene       [node]      Scene 引擎    process_scene
 |
 v
 character_subgraph             [subgraph]  角色决策+事件   character_subgraph
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

# LangGraph 核心 / LangGraph core
from langgraph.graph import END, StateGraph

# 服务层 / Service layer
from ..services import dm_service, message_service, scene_service

# 根状态定义 / Root state definition
from .state import OverallState

# 子图 / Subgraphs
from .subgraphs.character_subgraph import character_subgraph
from .subgraphs.reflection_subgraph import reflection_subgraph


def build_tick_graph() -> StateGraph:
    """构建主 tick 图：6 节点 + 条件分支 / Build main tick graph: 6 nodes + conditional edge."""
    # 创建状态图 / Create state graph
    graph = StateGraph(OverallState)

    # 注册 6 个节点 / Register 6 nodes
    graph.add_node("message_service.create_message", message_service.create_message)
    graph.add_node("dm_service.dm_create", dm_service.dm_create)
    graph.add_node("scene_service.process_scene", scene_service.process_scene)
    graph.add_node("character_subgraph", character_subgraph)
    graph.add_node("dm_service.dm_narrate", dm_service.dm_narrate)
    graph.add_node("reflection_subgraph", reflection_subgraph)

    # 顺序边 / Sequential edges
    graph.set_entry_point("message_service.create_message")
    graph.add_edge("message_service.create_message", "dm_service.dm_create")
    graph.add_edge("dm_service.dm_create", "scene_service.process_scene")
    graph.add_edge("scene_service.process_scene", "character_subgraph")
    graph.add_edge("character_subgraph", "dm_service.dm_narrate")

    # 条件分支：叙事后决定是否反思 / Conditional: reflect after narration?
    graph.add_conditional_edges(
        "dm_service.dm_narrate",
        lambda s: "reflection_subgraph" if s.get("needs_reflection") else END,
    )
    graph.add_edge("reflection_subgraph", END)

    return graph
