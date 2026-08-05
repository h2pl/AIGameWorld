"""TickGraph 主图 — 每个 tick 统一流程 / Uniform per-tick flow.

world 初始化（world_init）已移出主图：由 orchestrator.run_tick 在每 tick 入口前调用
world_init.ensure_world_initialized(world_id) 幂等完成（status==ready 自动跳过），
因此主图内所有 tick 走完全相同的流程，不再区分首 tick / 后续 tick。

START
 |
 v
load_data_subgraph                [node]     加载基础状态（world + pcs，不含场景）
 |
 v
party.discuss                    [node]     每个 tick：始终 LLM 多人对话，只交流信息
 |
 v
party.decide_scene               [node]     每个 tick：LLM 裁决是否切换主场景（持久化到 world）
 |
 v
data.load_scene
 |
 v
data.load_actors
 |
 v
data.load_scene_objects
 |
 v
tick_init.assign_positions       [node]     每个 tick：PC 出生点分配
 |
 v
dm_service.dm_create             [node]     每个 tick：DM 创造情境（产出 dm_record：plot_brief + hints）
 |
 v
tick_init.dm_create_event        [node]     每个 tick：构建 DM_CREATE 首事件（从 dm_record 填充真实内容）
 |
 v
tick_init.scene_setup_snapshot   [node]     每个 tick：截屏供 flush_events 构建 scene_setup
 |
 v
pc_subgraph                      [subgraph] 角色决策+行动
 |
 v
event_service.flush_events       [node]     PC 决策/行动事件构造
 |
 v
dm_service.dm_narrate            [node]     DM 叙事（dm_record 已由 dm_create 产出）
 |
 v
event_service.emit_narrative_event [node]   叙事 → DM_NARRATIVE 事件
 |
 v
data_service.camp_all            [node]     夜晚回营
 |
 v
data_service.persist_tick        [node]     数据持久化
 |
 v
END
"""

from langgraph.graph import END, StateGraph

from ..services import (
    data_service,
    dm_service,
    event_service,
    party_service,
    tick_init_service,
)
from ..utils.logging import get_logger
from .state import OverallState
from .subgraphs import load_data_subgraph as load_data_subgraph_module
from .subgraphs import pc_subgraph as pc_subgraph_module

logger = get_logger(__name__)


def build_tick_graph() -> StateGraph:
    """构建主 tick 图 / Build main tick graph.

    所有 tick 走统一流程（world 初始化已在图外由 ensure_world_initialized 完成）：
      load_data → party.discuss（LLM 讨论）→ party.decide_scene（LLM 决策切场景）
      → 场景加载 → PC 决策 → 事件/叙事/回营/持久化。
    无降级链路——任何节点抛错都会让本 tick 失败并向上传播。
    """
    logger.info("[graph] building tick graph")
    graph = StateGraph(OverallState)

    # ── 入口：加载基础状态（world + pcs，不含场景）──
    graph.add_node("load_data_subgraph", load_data_subgraph_module.load_data_subgraph)

    # ── 集体讨论 + 集体决策（每个 tick 都执行，两个独立节点）──
    graph.add_node("party.discuss", party_service.party_discuss)
    graph.add_node("party.decide_scene", party_service.party_decide_scene)

    # ── 公共 Phase ──
    graph.add_node("data.load_scene", data_service.load_scene)
    graph.add_node("data.load_actors", data_service.load_actors)
    graph.add_node("data.load_scene_objects", data_service.load_scene_objects)
    graph.add_node("tick_init.assign_positions", tick_init_service.assign_pc_positions)
    graph.add_node("dm_service.dm_create", dm_service.dm_create)
    graph.add_node("tick_init.dm_create_event", tick_init_service.build_dm_create_event)
    graph.add_node("tick_init.scene_setup_snapshot", tick_init_service.save_scene_setup_snapshot)

    # ── 角色决策 + 事件 + 叙事 + 回营 + 持久化 ──
    graph.add_node("pc_subgraph", pc_subgraph_module.pc_subgraph)
    graph.add_node("event_service.flush_events", event_service.flush_events)
    graph.add_node("dm_service.dm_narrate", dm_service.dm_narrate)
    graph.add_node("event_service.emit_narrative_event", event_service.emit_narrative_event)
    graph.add_node("data_service.camp_all", data_service.camp_all)
    graph.add_node("data_service.persist_tick", data_service.persist_tick)

    # ── 入口 → 集体讨论 → 集体决策 → 场景加载 ──
    graph.set_entry_point("load_data_subgraph")
    graph.add_edge("load_data_subgraph", "party.discuss")
    graph.add_edge("party.discuss", "party.decide_scene")
    graph.add_edge("party.decide_scene", "data.load_scene")

    # ── 公共 Phase ──
    graph.add_edge("data.load_scene", "data.load_actors")
    graph.add_edge("data.load_actors", "data.load_scene_objects")
    graph.add_edge("data.load_scene_objects", "tick_init.assign_positions")
    graph.add_edge("tick_init.assign_positions", "dm_service.dm_create")
    graph.add_edge("dm_service.dm_create", "tick_init.dm_create_event")
    graph.add_edge("tick_init.dm_create_event", "tick_init.scene_setup_snapshot")

    # ── 进入 PC 决策主链路（只改 state）──
    graph.add_edge("tick_init.scene_setup_snapshot", "pc_subgraph")  # 快照就绪，进入 PC 决策+行动
    graph.add_edge("pc_subgraph", "event_service.flush_events")  # PC 行动产出行事事件
    graph.add_edge("event_service.flush_events", "dm_service.dm_narrate")  # 事件就绪，DM 据此叙事
    graph.add_edge(
        "dm_service.dm_narrate", "event_service.emit_narrative_event"
    )  # 叙事文本就绪，产出 DM_NARRATIVE 事件
    graph.add_edge(
        "event_service.emit_narrative_event", "data_service.camp_all"
    )  # 叙事事件就绪，夜晚回营
    # 回营后由 persist_tick 统一落库（dm_records / events / pcs / actors / current_scene_id(备用镜像) / memories）
    graph.add_edge(
        "data_service.camp_all", "data_service.persist_tick"
    )  # 全部 state 就绪，统一落库
    graph.add_edge("data_service.persist_tick", END)  # 落库完成，tick 结束

    return graph
