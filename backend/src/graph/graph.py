"""TickGraph 主图 — Phase 顺序执行 / Sequential phase execution.

START
 |
 v
dm_service.dm_create              [node]      DM 创造情境
 |
 v
load_data_subgraph                [subgraph]  从 DB 加载 state
 |
 v
tick_init_subgraph                [subgraph]  tick 初始化（图DB/坐标/事件快照）
 |
 v
pc_subgraph                       [subgraph]  角色决策+行动
 |
 v
event_service.flush_events        [node]      PC 决策/行动事件构造
 |
 v
dm_service.dm_narrate             [node]      DM 叙事 → dm_record.dm_narrative
 |
 v
event_service.emit_narrative_event [node]     叙事 → DM_NARRATIVE 事件
 |
 v
data_service.persist_tick         [node]      数据持久化
 |
 v
END
"""

from langgraph.graph import END, StateGraph

from ..services import (
    data_service,
    dm_service,
    event_service,
)
from ..utils.logging import get_logger
from .state import OverallState
from .subgraphs import load_data_subgraph as load_data_subgraph_module
from .subgraphs import pc_subgraph as pc_subgraph_module
from .subgraphs import tick_init_subgraph as tick_init_subgraph_module

logger = get_logger(__name__)


def build_tick_graph() -> StateGraph:
    """构建主 tick 图 / Build main tick graph."""
    logger.info("[graph] building tick graph")
    graph = StateGraph(OverallState)

    graph.add_node("dm_service.dm_create", dm_service.dm_create)  # DM 创造情境
    graph.add_node("load_data_subgraph", load_data_subgraph_module.load_data_subgraph)  # 数据加载子图
    graph.add_node("tick_init_subgraph", tick_init_subgraph_module.tick_init_subgraph)  # tick 初始化子图
    graph.add_node("pc_subgraph", pc_subgraph_module.pc_subgraph)  # 角色决策子图
    graph.add_node("event_service.flush_events", event_service.flush_events)  # 事件构造
    graph.add_node("dm_service.dm_narrate", dm_service.dm_narrate)  # DM 叙事
    graph.add_node("event_service.emit_narrative_event", event_service.emit_narrative_event)  # 叙事事件
    graph.add_node("data_service.persist_tick", data_service.persist_tick)  # 数据持久化

    graph.set_entry_point("dm_service.dm_create")  # 入口节点
    graph.add_edge("dm_service.dm_create", "load_data_subgraph")  # 创建 → 加载
    graph.add_edge("load_data_subgraph", "tick_init_subgraph")  # 加载 → 初始化
    graph.add_edge("tick_init_subgraph", "pc_subgraph")  # 初始化 → 决策
    graph.add_edge("pc_subgraph", "event_service.flush_events")  # 决策 → 事件
    graph.add_edge("event_service.flush_events", "dm_service.dm_narrate")  # 事件 → 叙事
    graph.add_edge("dm_service.dm_narrate", "event_service.emit_narrative_event")  # 叙事 → 叙事事件
    graph.add_edge("event_service.emit_narrative_event", "data_service.persist_tick")  # 叙事事件 → 持久化
    graph.add_edge("data_service.persist_tick", END)  # 持久化 → 结束

    return graph
