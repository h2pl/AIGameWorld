"""TickGraph 主图 — Phase 顺序执行 + 条件分支.

START
 |
 v
 message_service.create_tick_message     [node]      创建消息       create_tick_message
 |
 v
 dm_service.dm_create              [node]      DM 创造情境   dm_create
 |
 v
 scene_service.build_scene_info    [node]      构建场景信息  build_scene_info
 |
 v
 character_subgraph             [subgraph]  角色决策+行动   character_subgraph
 |
 v
 dm_service.dm_narrate             [node]      DM 叙事       dm_narrate
 |
 +-- needs_reflection? --False--> event_service.flush_events
 |
 True
 |
 v
 reflection_service.reflect        [node]      角色反思     reflect
 |
 v
 event_service.flush_events        [node]      落盘事件     flush_events
 |
 v
 END
"""

# LangGraph 核心 / LangGraph core
from langgraph.graph import END, StateGraph

# 服务层 / Service layer
from ..services import dm_service, event_service, message_service, reflection_service, scene_service

# 根状态定义 / Root state definition
from .state import OverallState

# 子图 / Subgraphs
from .subgraphs import character_subgraph as character_subgraph_module


def build_tick_graph() -> StateGraph:
    """构建主 tick 图：7 节点 + 条件分支 / Build main tick graph: 7 nodes + conditional edge."""
    # 创建状态图 / Create state graph
    graph = StateGraph(OverallState)

    # 注册 7 个节点 / Register 7 nodes
    graph.add_node("message_service.create_tick_message", message_service.create_tick_message)
    graph.add_node("dm_service.dm_create", dm_service.dm_create)
    graph.add_node("scene_service.build_scene_info", scene_service.build_scene_info)
    graph.add_node("character_subgraph", character_subgraph_module.character_subgraph)
    graph.add_node("dm_service.dm_narrate", dm_service.dm_narrate)
    graph.add_node("reflection_service.reflect", reflection_service.reflect)
    graph.add_node("event_service.flush_events", event_service.flush_events)

    # 顺序边 / Sequential edges
    graph.set_entry_point("message_service.create_tick_message")
    graph.add_edge("message_service.create_tick_message", "dm_service.dm_create")
    graph.add_edge("dm_service.dm_create", "scene_service.build_scene_info")
    graph.add_edge("scene_service.build_scene_info", "character_subgraph")
    graph.add_edge("character_subgraph", "dm_service.dm_narrate")

    # 条件分支：叙事后决定是否反思，最终都汇入 event_service 统一落盘事件 /
    # Conditional: reflect after narration?  Both branches converge on event_service to flush events.
    graph.add_conditional_edges(
        "dm_service.dm_narrate",
        lambda s: (
            "reflection_service.reflect"
            if s.get("needs_reflection")
            else "event_service.flush_events"
        ),
    )
    graph.add_edge("reflection_service.reflect", "event_service.flush_events")
    graph.add_edge("event_service.flush_events", END)

    return graph
