"""Data Service: 统一负责 tick 开始/结束时的 DB 读写 / Centralized DB read/write at tick boundaries.

tick 开始时读取 graph 需要的状态：
  load_world → load_scene → load_actors → load_pcs → load_scene_objects

tick 末尾持久化全部数据：
  persist_tick 写 dm_records / tick_events / PC / Actor / memories
"""

from langchain_core.runnables.config import RunnableConfig

from ..domain import Memory
from ..domain.dm_record import DMRecord
from ..graph.state import OverallState
from ..utils.helpers import get_repo, is_mock
from ..utils.logging import get_logger, trace_node

logger = get_logger(__name__)


# ── tick 开始时从 DB 读取状态 ────────────────────────────────────────────────


@trace_node("data.load_world")
async def load_world(state: OverallState, config=None) -> dict:
    """从 DB 读取 World 领域模型 / Load world from DB."""
    world_id = state.get("world_id", "")
    world_repo = get_repo(config, "world")
    world = await world_repo.get(world_id) if world_repo else None
    return {"world": world} if world else {}


@trace_node("data.load_scene")
async def load_scene(state: OverallState, config=None) -> dict:
    """从 DB 读取当前场景 Scene 领域模型 / Load scene from DB（使用 dm_record.scene_id，此时 scene 还未加载）."""
    dm = state.get("dm_record")
    scene_id = dm.scene_id if dm else ""
    scene_repo = get_repo(config, "scene")
    scene = await scene_repo.get_scene(scene_id) if scene_repo else None
    return {"scene": scene}


@trace_node("data.load_actors")
async def load_actors(state: OverallState, config=None) -> dict:
    """从 DB 读取当前场景 Actor 的领域模型 map / Load actors from DB, filtered by scene_id."""
    scene = state.get("scene")
    if scene is None:
        return {"actors": {}}
    world_id = state.get("world_id", "")
    actor_repo = get_repo(config, "actor")
    actors = await actor_repo.load_all(world_id) if world_id and actor_repo else []
    scene_actors = [actor for actor in actors if getattr(actor, "scene_id", "") == scene.id]
    return {"actors": {actor.id: actor for actor in scene_actors}}


@trace_node("data.load_pcs")
async def load_pcs(state: OverallState, config=None) -> dict:
    """从 DB 读取全部 PC 的领域模型 map / Load all PCs from DB."""
    world_id = state.get("world_id", "")
    pc_repo = get_repo(config, "char")
    if not pc_repo:
        return {"pcs": {}}
    pcs = await pc_repo.load_all(world_id) if world_id else []
    return {"pcs": {pc.id: pc for pc in pcs}}


@trace_node("data.load_scene_objects")
async def load_scene_objects(state: OverallState, config=None) -> dict:
    """从 DB 读取场景物体列表 / Load scene objects from DB."""
    scene = state.get("scene")
    if scene is None:
        return {"scene_objects": []}
    scene_repo = get_repo(config, "scene")
    if not scene_repo:
        return {"scene_objects": []}

    object_ids = await scene_repo.get_object_ids(scene.id)
    if not object_ids:
        return {"scene_objects": []}
    all_objects = await scene_repo.load_all()
    scene_objects = [all_objects[oid] for oid in object_ids if oid in all_objects]
    return {"scene_objects": scene_objects}


# ── tick 末尾持久化 ─────────────────────────────────────────────────────────


@trace_node("data.persist")
async def persist_tick(state: OverallState, config: RunnableConfig = None) -> dict:
    """tick 末尾：落盘全部数据 / Tick end: persist all data."""

    tick = state.get("tick", 0)
    world_id = state.get("world_id", "")

    # 1. 写 dm_records / Write DM record
    dm_record = state.get("dm_record")
    if isinstance(dm_record, DMRecord) and world_id:
        record_repo = get_repo(config, "dm_record")
        if record_repo:
            await record_repo.save_plot_brief(dm_record)
            logger.info("[data] wrote dm_record tick=%s", tick)

    # 2. 写事件到 tick_events / Write events to tick_events
    events: list = state.get("tick_events", [])
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
    # Mock 模式下跳过 Chroma/SQLite 持久化，避免 embedding 写入拖慢 E2E
    memories: dict[str, list[Memory]] = state.get("memories", {})
    if memories and not is_mock(config):
        memory_repo = get_repo(config, "memory")
        if memory_repo:
            total = 0
            for pc_id, mems in memories.items():
                for m in mems:
                    await memory_repo.store(
                        pc_id=m.pc_id or pc_id,
                        content=m.content,
                        tick=m.tick,
                        importance=m.importance,
                        memory_type=m.memory_type,
                        period=m.period,
                        entity_type=m.entity_type,
                        world_id=m.world_id or world_id,
                    )
                    total += 1
            logger.info("[data] persisted memories count=%d tick=%s", total, tick)

    return {}
