"""TickGraph 主图 — Phase 顺序执行 / Sequential phase execution.

START
 |
 v
 dm_service.dm_create              [node]      DM 创造情境   dm_create
 |
 v
 scene_service.build_scene_info    [node]      构建场景信息  build_scene_info
 |
 v
 pc_subgraph                       [subgraph]  角色决策+行动   pc_subgraph
 |
 v
 event_service.flush_events        [node]      构造事件     flush_events
 |
 v
 data_service.persist_tick         [node]      数据持久化   persist_tick
 |
 v
 END
"""

# LangGraph 核心 / LangGraph core
from langgraph.graph import END, StateGraph

# 服务层 / Service layer
from ..services import data_service, dm_service, event_service, scene_service
from ..utils.logging import get_logger

# 根状态定义 / Root state definition
from .state import OverallState

# 子图 / Subgraphs
from .subgraphs import pc_subgraph as pc_subgraph_module

logger = get_logger(__name__)


def build_tick_graph() -> StateGraph:
    """构建主 tick 图：5 节点 / Build main tick graph: 5 nodes."""
    logger.info("[graph] building tick graph")
    graph = StateGraph(OverallState)

    graph.add_node("dm_service.dm_create", dm_service.dm_create)
    graph.add_node("scene_service.build_scene_info", scene_service.build_scene_info)
    graph.add_node("pc_subgraph", pc_subgraph_module.pc_subgraph)
    graph.add_node("event_service.flush_events", event_service.flush_events)
    graph.add_node("data_service.persist_tick", data_service.persist_tick)

    graph.set_entry_point("dm_service.dm_create")
    graph.add_edge("dm_service.dm_create", "scene_service.build_scene_info")
    graph.add_edge("scene_service.build_scene_info", "pc_subgraph")
    graph.add_edge("pc_subgraph", "event_service.flush_events")
    graph.add_edge("event_service.flush_events", "data_service.persist_tick")
    graph.add_edge("data_service.persist_tick", END)

    return graph
