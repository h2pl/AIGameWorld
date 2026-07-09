"""TickGraph 主图 — Phase 顺序执行 / Sequential phase execution.

START
 |
 v
 dm_service.dm_create              [node]      DM 创造情境
 |
 v
 load_data_subgraph                [subgraph]  从 DB 加载 state + tick_init 事件
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
    reflection_service,
)
from ..utils.logging import get_logger
from .state import OverallState
from .subgraphs import load_data_subgraph as load_data_subgraph_module
from .subgraphs import pc_subgraph as pc_subgraph_module

logger = get_logger(__name__)


def build_tick_graph() -> StateGraph:
    """构建主 tick 图 / Build main tick graph."""
    logger.info("[graph] building tick graph")
    graph = StateGraph(OverallState)

    graph.add_node("dm_service.dm_create", dm_service.dm_create)
    graph.add_node("load_data_subgraph", load_data_subgraph_module.load_data_subgraph)
    graph.add_node("pc_subgraph", pc_subgraph_module.pc_subgraph)
    graph.add_node("event_service.flush_events", event_service.flush_events)
    graph.add_node("dm_service.dm_narrate", dm_service.dm_narrate)
    graph.add_node("event_service.emit_narrative_event", event_service.emit_narrative_event)
    graph.add_node("data_service.persist_tick", data_service.persist_tick)
    graph.add_node("reflection_service.reflect", reflection_service.reflect)

    graph.set_entry_point("dm_service.dm_create")
    graph.add_edge("dm_service.dm_create", "load_data_subgraph")
    graph.add_edge("load_data_subgraph", "pc_subgraph")
    graph.add_edge("pc_subgraph", "event_service.flush_events")
    graph.add_edge("event_service.flush_events", "dm_service.dm_narrate")
    graph.add_edge("dm_service.dm_narrate", "event_service.emit_narrative_event")
    graph.add_edge("event_service.emit_narrative_event", "data_service.persist_tick")
    graph.add_edge("data_service.persist_tick", "reflection_service.reflect")
    graph.add_edge("reflection_service.reflect", END)

    return graph
