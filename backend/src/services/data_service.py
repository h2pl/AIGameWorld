"""Data Service: 负责 tick 末尾所有数据持久化 / Persists all data at tick end.

event_service.flush_events 负责构造事件，data_service.persist_tick 负责写入 DB：
1. 写入 dm_records
2. 写入 tick_events
3. 写入变更的 PC 状态
"""

from typing import Any

from langchain_core.runnables.config import RunnableConfig

from ..domain.dm_record import DMRecord
from ..graph.state import OverallState
from ..utils.helpers import get_repo
from ..utils.logging import get_logger, trace_node

logger = get_logger(__name__)


@trace_node("data.persist")
async def persist_tick(state: OverallState, config: RunnableConfig = None) -> dict:
    """tick 末尾：落盘全部数据 / Tick end: persist all data."""

    tick = state.get("tick", 0)
    world_id = state.get("world_id", "")

    # 1. 写 dm_records / Write DM record
    dm_ext = state.get("_dm_ext")
    if dm_ext and world_id:
        record_repo = get_repo(config, "dm_record")
        if record_repo:
            await record_repo.save_plot_brief(
                DMRecord(
                    world_id=world_id,
                    tick=tick,
                    plot_brief=state.get("plot_brief", ""),
                    hints=state.get("hints", []),
                    ext=dm_ext,
                )
            )
            logger.info("[data] wrote dm_record tick=%s", tick)

    # 2. 写事件到 tick_events / Write events to tick_events
    events: list = state.get("_pending_events", [])
    if events:
        event_repo = get_repo(config, "event")
        if event_repo:
            await event_repo.insert_tick_events(tick, events, world_id=world_id)
            logger.info("[data] wrote events tick=%s count=%d", tick, len(events))

    # 3. 持久化 PC 运行时状态 / Persist PC runtime state
    pc_state_map: dict[str, dict[str, Any]] = state.get("pc_state_map", {})
    if pc_state_map:
        pc_repo = get_repo(config, "char")
        if pc_repo:
            for pc_id, info in pc_state_map.items():
                pc = await pc_repo.load_pc(pc_id)
                if pc:
                    pc.position_x = info.get("position_x", 0)
                    pc.position_y = info.get("position_y", 0)
                    if "scene_id" in info:
                        pc.scene_id = info["scene_id"]
                    await pc_repo.save_pc(pc)
            logger.info("[data] persisted pc_state_map count=%d tick=%s", len(pc_state_map), tick)

    return {}
