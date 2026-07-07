"""Scene Service: State ↔ Engine adapter.

负责在 tick 开始时构建场景相关的领域模型并写入 state：
- scene: 单场景信息 dict
- scene_objects: 场景物体 list
- actors: Actor 领域模型 map
- pcs: PlayerCharacter 领域模型 map

使用领域模型而非 model_dump 后的 dict，方便各节点直接读写全量信息，
也便于 data_service 在 tick 末尾直接 save() 落盘。
"""

from typing import Any

from ..domain import Actor, PlayerCharacter, Scene
from ..graph.state import OverallState
from ..utils.helpers import build_occupied_set, find_vacant_adjacent, get_repo
from ..utils.logging import get_logger, trace_node

logger = get_logger(__name__)


@trace_node("scene.build_scene_state")
async def build_scene_state(state: OverallState, config=None) -> dict:
    """Phase 1.5: 顺序调用 6 个场景方法，构建完整场景信息 / Sequential wrapper."""
    tick = state.get("tick", 0)
    scene_id = state.get("scene_id", "")
    logger.info("[service] tick=%s scene_id=%s", tick, scene_id)

    result: dict[str, Any] = {}
    result.update(await build_scene_info(state, config))
    result.update(await build_actors({**state, **result}, config))
    result.update(await build_pcs({**state, **result}, config))
    result.update(await build_scene_objects({**state, **result}, config))
    return result


@trace_node("scene.build_scene_info")
async def build_scene_info(state: OverallState, config=None) -> dict:
    """第一步：构建单场景信息 / Build single scene context."""
    scene_id = state.get("scene_id", "")
    world_id = state.get("world_id", "")
    scene_repo = get_repo(config, "scene")
    scene = await scene_repo.get_scene(scene_id) if scene_repo else None
    if scene is None:
        scene = Scene(
            id=scene_id,
            name="",
            type="",
            description="",
            spawn_x=0,
            spawn_y=0,
            map_width=40,
            map_height=40,
            tilemap_summary="",
            landmarks=[],
            exits=[],
            world_id=world_id,
        )
        if scene_repo:
            await scene_repo.save_scene(scene, world_id)
    return {"scene": scene}


@trace_node("scene.build_actors")
async def build_actors(state: OverallState, config=None) -> dict:
    """第二步：构建 Actor 领域模型 map / Build actor domain model map."""
    scene_id = state.get("scene_id", "")
    world_id = state.get("world_id", "")
    actor_repo = get_repo(config, "actor")
    actors = await actor_repo.load_all(world_id) if world_id and actor_repo else []
    scene_actors = [actor for actor in actors if getattr(actor, "scene_id", "") == scene_id]
    return {"actors": {actor.id: actor for actor in scene_actors}}


@trace_node("scene.build_pcs")
async def build_pcs(state: OverallState, config=None) -> dict:
    """第三步：构建 PC 领域模型 map，含坐标分配 / Build PC domain model map with position assignment."""
    scene_id = state.get("scene_id", "")
    world_id = state.get("world_id", "")
    pc_repo = get_repo(config, "char")
    if not pc_repo or not scene_id:
        return {"pcs": {}}

    pcs = await pc_repo.load_all(world_id) if world_id else []
    scene = state.get("scene")
    actors = state.get("actors", {})

    pc_positions = await _assign_pc_positions(pcs, scene, pc_repo, actors=actors, spawn_radius=2)

    pc_map: dict[str, PlayerCharacter] = {}
    for pc in pcs:
        pos = pc_positions.get(pc.id)
        if pos:
            pc.position_x = pos["x"]
            pc.position_y = pos["y"]
        pc.scene_id = scene_id
        pc_map[pc.id] = pc

    return {"pcs": pc_map}


@trace_node("scene.build_scene_objects")
async def build_scene_objects(state: OverallState, config=None) -> dict:
    """第四步：构建场景物体 list / Build scene object list."""
    scene_id = state.get("scene_id", "")
    scene_repo = get_repo(config, "scene")
    if not scene_repo or not scene_id:
        return {"scene_objects": []}

    object_ids = await scene_repo.get_object_ids(scene_id)
    scene_objects = await _fetch_scene_objects(object_ids, scene_repo)
    return {"scene_objects": scene_objects}


async def _assign_pc_positions(
    pcs: list[PlayerCharacter],
    scene: Scene | None,
    pc_repo,
    actors: dict[str, Actor] | None = None,
    spawn_radius: int = 2,
) -> dict[str, dict[str, int]]:
    """把未设置坐标的 PC 分配到场景出生点附近，返回 id→{x,y} 映射.

    以 spawn 为中心螺旋搜索空位，避免与已定位 PC/Actor 重叠。
    坐标(0,0) 或 scene_id 不匹配当前场景的 PC 视为未设置，分配到新场景出生点。
    """
    scene_id = scene.id if scene else ""
    unset_pcs = [
        pc
        for pc in pcs
        if (pc.position_x == 0 and pc.position_y == 0) or getattr(pc, "scene_id", "") != scene_id
    ]
    if not unset_pcs:
        return {}

    spawn_x = scene.spawn_x if scene else 0
    spawn_y = scene.spawn_y if scene else 0

    occupied = build_occupied_set(
        {pc.id: pc for pc in pcs if pc not in unset_pcs}, actors, exclude_id=""
    )

    positions: dict[str, dict[str, int]] = {}
    offsets = [
        (dx, dy)
        for radius in range(spawn_radius + 1)
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
        if max(abs(dx), abs(dy)) == radius
    ]

    for pc in unset_pcs:
        x, y = spawn_x, spawn_y
        for dx, dy in offsets:
            candidate = (spawn_x + dx, spawn_y + dy)
            if candidate not in occupied:
                x, y = candidate
                break
        else:
            x, y = find_vacant_adjacent(spawn_x, spawn_y, occupied)

        pc.position_x = x
        pc.position_y = y
        positions[pc.id] = {"x": x, "y": y}
        occupied.add((x, y))

    return positions


async def _fetch_scene_objects(object_ids: list[str], scene_repo) -> list:
    """按 id 列表查询场景物体 / Fetch scene objects by ids."""
    if not scene_repo or not object_ids:
        return []
    all_objects = await scene_repo.load_all()
    return [all_objects[oid] for oid in object_ids if oid in all_objects]
