"""Data Service: 统一负责 tick 开始/结束时的 DB 读写 / Centralized DB read/write at tick boundaries.

tick 开始时读取 graph 需要的状态：
  load_world → load_scene → load_actors → load_pcs → load_scene_objects

tick 末尾持久化全部数据：
  persist_tick 写 dm_records / tick_events / PC / Actor / memories
"""

from langchain_core.runnables.config import RunnableConfig

from ..domain import Memory
from ..domain.dm_record import DMRecord
from ..domain.event import TickEvent, TickEventType
from ..graph.state import OverallState
from ..utils.helpers import assign_spawn_positions, get_repo, is_mock
from ..utils.logging import get_logger, trace_node

logger = get_logger(__name__)


# ── tick 开始时从 DB 读取状态 ────────────────────────────────────────────────


@trace_node("data.load_world")
async def load_world(state: OverallState, config=None) -> dict:
    """从 DB 读取 World 领域模型，并恢复当前主场景 current_scene_id / Load world + current scene."""
    world_id = state.get("world_id", "")
    world_repo = get_repo(config, "world")
    world = await world_repo.get(world_id) if world_repo else None
    if not world:
        return {}
    # current_scene_id 从 world.current_scene_id 恢复进 state（该字段仅作备用记录，
    # 真正驱动场景的是 party.decide_scene 在 state 内流转的结果，由 persist_tick 在末尾镜像写回）
    return {"world": world, "current_scene_id": world.current_scene_id}


@trace_node("data.load_scene")
async def load_scene(state: OverallState, config=None) -> dict:
    """从 DB 读取当前场景 Scene 领域模型 / Load scene from DB.

    场景来源：current_scene_id 由 load_world 从 world.current_scene_id 恢复进 state（备用记录），
    后续每 tick 由 party.decide_scene 在 state 内流转，persist_tick 末尾再镜像写回 world。
    world_init 由 status 守卫保证在首个 tick 前已执行，因此 current_scene_id 必有值，
    这是确定性路径，不做「fallback to first scene」之类的错误路径兜底。
    """
    scene_id = state.get("current_scene_id", "")
    if not scene_id:
        raise ValueError(
            "[data] current_scene_id is empty — world_init was not run (status guard broken)"
        )

    scene_repo = get_repo(config, "scene")
    if not scene_repo:
        return {"scene": None, "current_scene_id": scene_id}

    scene = await scene_repo.get_scene(scene_id)
    return {"scene": scene, "current_scene_id": scene_id}


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

    # 5. 顺带把当前主场景记到 world.current_scene_id（备用，非权威来源；
    #    真正驱动每 tick 场景的是 state.current_scene_id，由 party.decide_scene 在 state 内流转）
    current_scene_id = state.get("current_scene_id", "")
    if world_id and current_scene_id:
        world_repo = get_repo(config, "world")
        if world_repo:
            await world_repo.set_current_scene_id(world_id, current_scene_id)
            logger.info(
                "[data] mirrored current_scene_id=%s to world tick=%s", current_scene_id, tick
            )

    # 6. 统一落盘本 tick 产生的新记忆 / Persist new memories created this tick
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
                        current_tick=tick,
                    )
                    total += 1
            logger.info("[data] persisted memories count=%d tick=%s", total, tick)

    return {}


@trace_node("data.camp_all")
async def camp_all(state: OverallState, config=None) -> dict:
    """tick 末尾：夜晚降临，所有 PC 回到当前场景出生点（营地）休息.

    重置每位 PC 坐标到场景 spawn 附近，产出 PARTY_CAMP 事件（携带 PC 新坐标），
    供前端把 sprite 移回出生点并播放旁白。坐标修改直接作用于 pcs 领域模型，
    由 persist_tick 落盘，作为下一 tick 的起点。
    """
    scene = state.get("scene")
    pcs = state.get("pcs", {})
    actors = state.get("actors", {})
    if not pcs or scene is None:
        return {}

    # 重置所有 PC 到出生点 / Reset all PCs to spawn
    pc_list = list(pcs.values())
    assign_spawn_positions(pc_list, scene, actors)
    for pc in pc_list:
        pcs[pc.id] = pc

    camp_event = TickEvent(
        type=TickEventType.PARTY_CAMP,
        tick=state.get("tick", 0),
        world_id=state.get("world_id", ""),
        payload={
            "scene_id": scene.id,
            "scene_name": getattr(scene, "name", ""),
            "pcs": [
                {
                    "pc_id": pc.id,
                    "pc_name": pc.name,
                    "position_x": pc.position_x,
                    "position_y": pc.position_y,
                }
                for pc in pc_list
            ],
            "narration": "夜幕降临，冒险者们回到营地，围坐在篝火旁休整，为明日的旅程养精蓄锐。",
        },
    )
    prev = list(state.get("tick_events", []))
    return {"pcs": pcs, "tick_events": [*prev, camp_event]}
