"""DM Service: State ↔ Engine adapter."""

from langchain_core.runnables.config import RunnableConfig

from ..engine.dm import dm_engine
from ..graph.state import OverallState
from ..utils.logging import trace_node


@trace_node("dm.create")
async def dm_create(state: OverallState, config: RunnableConfig = None) -> dict:
    """Phase 1: DM 创造情境 / DM creates the situation.

    dm_create 引擎产出本 tick 的 plot_brief + hints（存入 dm_record）。
    场景由 world_init / party.decide_scene 确定，当前场景 scene_id 直接写入
    dm_record.scene_id，供 build_dm_create_event 与 persist_tick 使用。
    """
    tick = state.get("tick", 0)
    world_id = state.get("world_id", "")
    prev_dm = state.get("dm_record")
    dm_record = await dm_engine.dm_create(
        tick=tick,
        plot_brief=prev_dm.plot_brief if prev_dm else "",
        prev_narrative=prev_dm.dm_narrative if prev_dm else "",
        world_id=world_id,
        config=config,
    )
    # 回填当前主场景到 dm_record，供事件构造与落库 / Backfill scene_id for event + persistence
    dm_record.scene_id = state.get("current_scene_id", "")
    return {"dm_record": dm_record}


@trace_node("dm.narrate")
async def dm_narrate(state: OverallState, config: RunnableConfig = None) -> dict:
    """Phase 6: DM 叙事——产出 narrative 写入 dm_record.

    dm_create 引擎（dm_service.dm_create）已接入主链路，位于 dm_create_event 之前，
    本 tick 的 dm_record 由 dm_create 保证有值（plot_brief + hints），dm_narrate
    据此产出叙事。dm_record 缺失（mock 异常等防御路径）时直接返回，不产出叙事。
    """
    dm = state.get("dm_record")
    if dm is None:
        return {}

    pcs = state.get("pcs", {})
    actors = state.get("actors", {})
    scene = state.get("scene")
    scene_objects = state.get("scene_objects", [])
    actions = state.get("actions", [])
    tick_events = state.get("tick_events", [])
    narrative = await dm_engine.dm_narrate(
        tick=state.get("tick", 0),
        world_id=state.get("world_id", ""),
        plot_brief=dm.plot_brief if dm else "",
        hints=dm.hints if dm else [],
        prev_narrative=dm.dm_narrative if dm else "",
        events=tick_events,
        scene=scene,
        scene_objects=scene_objects,
        pcs=pcs,
        actors=actors,
        actions=actions,
        config=config,
    )
    dm.dm_narrative = narrative
    return {"dm_record": dm}
