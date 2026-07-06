"""Data Service: 负责 tick 末尾所有数据持久化 / Persists all data at tick end.

event_service.flush_events 负责构造事件，data_service.persist_tick 负责写入 DB：
1. 写入 dm_records
2. 写入 tick_events
3. 写入变更的 PC 状态
4. 写入变更的 Actor 状态（死亡/hp 等）
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

    # 3. 持久化 PC 领域模型 / Persist PC domain models
    pcs = state.get("pcs", {})
    if pcs:
        pc_repo = get_repo(config, "char")
        if pc_repo:
            for pc in pcs.values():
                await pc_repo.save(pc)
            logger.info("[data] persisted pcs count=%d tick=%s", len(pcs), tick)

    # 4. 持久化 Actor 领域模型 / Persist Actor domain models
    actors = state.get("actors", {})
    if actors:
        actor_repo = get_repo(config, "actor")
        if actor_repo:
            for actor in actors.values():
                await actor_repo.save(actor)
            logger.info("[data] persisted actors count=%d tick=%s", len(actors), tick)

    # 5. 统一落盘本 tick 产生的新记忆 / Persist new memories created this tick
    pc_memory_map: dict[str, list[dict[str, Any]]] = state.get("pc_memory_map", {})
    if pc_memory_map:
        memory_repo = get_repo(config, "memory")
        if memory_repo:
            total = 0
            for pc_id, mems in pc_memory_map.items():
                for m in mems:
                    await memory_repo.store(
                        pc_id=m.get("pc_id", pc_id),
                        content=m.get("content", ""),
                        tick=m.get("tick", tick),
                        importance=m.get("importance", 2),
                        memory_type=m.get("memory_type", "observation"),
                        period=m.get("period", ""),
                        entity_type=m.get("entity_type", "pc"),
                        world_id=m.get("world_id", world_id),
                    )
                    total += 1
            logger.info("[data] persisted memories count=%d tick=%s", total, tick)

    return {}
