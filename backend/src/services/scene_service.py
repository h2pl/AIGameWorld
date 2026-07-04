"""Scene Service: State ↔ Engine adapter.

这里也负责构建并注入场景信息（当前场景的场景/物体/角色完整信息）到 state，
因为它描述的是场景本身的信息，与谁来使用无关（不区分 PC，也不做距离限制，
同场景的人和物都能看到），属于场景处理阶段的产物，不应该放进角色决策阶段。
返回完整信息而非仅 id，供 decision_engine 等下游直接消费，无需再查 repo /
This also builds and injects scene info (full scene/object/pc info for
the current scene) into state, since it describes the scene itself
(consumer-independent — not per-PC, no distance limit; anyone/anything in the
same scene is visible) and belongs to the scene-processing phase, not the
pc-decision phase. Full info (not just ids) is returned so downstream
consumers like decision_engine can use it directly without querying repos
again.
"""

from typing import Any

from ..domain.player_character import PlayerCharacter
from ..graph.state import OverallState
from ..utils.helpers import get_repo
from ..utils.logging import get_logger, trace_node

logger = get_logger(__name__)


@trace_node("scene.build")
async def build_scene_info(state: OverallState, config=None) -> dict:
    """Phase 1.5: 构建当前场景的完整信息并注入 state /
    Build the current scene's full info and inject it into state."""
    tick = state.get("tick", 0)
    scene_id = state.get("scene_id", "")
    tick_message_id = state.get("tick_message_id", "")
    logger.info("[service] tick=%s scene_id=%s tick_message_id=%s", tick, scene_id, tick_message_id)
    info, pc_state_map = await _build_scene_info(state, config)
    return {"scene_info": info, "pc_state_map": pc_state_map}


async def _build_scene_info(state: OverallState, config=None) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """一次性构建当前场景的完整信息 + PC 运行时状态 map /
    Build the current scene's full info + PC runtime state map in one pass."""
    scene_id = state.get("scene_id", "")
    world_id = state.get("world_id", "")
    pc_repo = get_repo(config, "char")
    scene_repo = get_repo(config, "scene")
    if not pc_repo or not scene_id:
        return {}, {}

    pcs = await pc_repo.load_pcs(world_id) if world_id else []
    actors = await pc_repo.load_actors(world_id) if world_id else []
    # 当前场景内的角色池 / Character pool limited to the current scene
    scene_pcs = [pc for pc in pcs if getattr(pc, "scene_id", "") == scene_id]
    scene_actors = [actor for actor in actors if getattr(actor, "scene_id", "") == scene_id]

    scene = await scene_repo.get_scene(scene_id) if scene_repo else None
    scene_ctx = _build_scene_ctx(scene, scene_id)
    scene_object_ids = await scene_repo.get_object_ids(scene_id) if scene_repo else []
    scene_objects = await _fetch_scene_objects(scene_object_ids, scene_repo)
    scene_object_ctx = _build_scene_object_ctx(scene_objects)

    # 按场景出生点给未设置坐标的 PC 分配坐标，避免重叠 / Assign positions to unset PCs
    pc_positions = await _assign_pc_positions(scene_pcs, scene, pc_repo, spawn_radius=1)

    # 构建 PC 运行时状态 map（tick 内各引擎读写此 map，末尾统一入库）
    # / Build PC runtime state map (engines read/write during tick, persisted at tick end)
    pc_state_map: dict[str, dict[str, Any]] = {}
    for pc in scene_pcs:
        pos = pc_positions.get(pc.id, {"x": pc.position_x, "y": pc.position_y})
        pc_state_map[pc.id] = {
            "position_x": pos["x"],
            "position_y": pos["y"],
            "scene_id": scene_id,
            "status": pc.status,
        }

    return {
        "scene": scene_ctx,
        "scene_objects": scene_object_ctx,
        "pcs": [_build_pc_ctx(pc, pc_positions) for pc in scene_pcs],
        "actors": _build_actor_ctx(scene_actors),
        "pc_positions": pc_positions,
    }, pc_state_map


async def _assign_pc_positions(
    pcs: list[PlayerCharacter],
    scene: dict | None,
    pc_repo,
    spawn_radius: int = 1,
) -> dict[str, dict[str, int]]:
    """把未设置坐标的 PC 分配到场景出生点附近，返回 id→{x,y} 映射.

    以 spawn 为中心，在 (2*radius+1)^2 的范围内按顺序占位，避免重叠。
    NPC 保持 mock 或 world-pack 中的固定坐标，不参与分配。
    """
    unset_pcs = [pc for pc in pcs if pc.position_x == 0 and pc.position_y == 0]
    if not unset_pcs:
        return {}

    spawn_x = scene.get("spawn_x", 0) if scene else 0
    spawn_y = scene.get("spawn_y", 0) if scene else 0

    positions: dict[str, dict[str, int]] = {}
    # 生成以 spawn 为中心的格子偏移序列 / Generate offset grid around spawn
    offsets = [
        (dx, dy)
        for dy in range(-spawn_radius, spawn_radius + 1)
        for dx in range(-spawn_radius, spawn_radius + 1)
    ]

    for i, pc in enumerate(unset_pcs):
        dx, dy = offsets[i % len(offsets)]
        x = spawn_x + dx
        y = spawn_y + dy
        pc.position_x = x
        pc.position_y = y
        positions[pc.id] = {"x": x, "y": y}
        # 持久化新坐标 / Persist updated position
        if pc_repo:
            await pc_repo.save_pc(pc)

    return positions


async def _fetch_scene_objects(object_ids: list[str], scene_repo) -> list:
    """按 id 列表查询场景物体 / Fetch scene objects by ids."""
    if not scene_repo or not object_ids:
        return []
    all_objects = await scene_repo.load_all()
    return [all_objects[oid] for oid in object_ids if oid in all_objects]


def _build_scene_ctx(scene: dict | None, scene_id: str) -> dict[str, Any]:
    if not scene:
        return {
            "id": scene_id,
            "name": "",
            "type": "",
            "description": "",
            "spawn_x": 0,
            "spawn_y": 0,
            "map_width": 40,
            "map_height": 40,
            "landmarks": [],
            "exits": [],
        }
    return {
        "id": scene.get("id", scene_id),
        "name": scene.get("name", ""),
        "type": scene.get("type", ""),
        "description": scene.get("description", ""),
        "map_key": scene.get("map_key", ""),
        "spawn_x": scene.get("spawn_x", 0),
        "spawn_y": scene.get("spawn_y", 0),
        "map_width": scene.get("map_width", 40),
        "map_height": scene.get("map_height", 40),
        "landmarks": scene.get("landmarks", []),
        "exits": scene.get("exits", []),
    }


def _build_scene_object_ctx(objects: list) -> list[dict[str, Any]]:
    return [
        {
            "id": obj.id,
            "name": obj.name,
            "object_type": obj.object_type.value,
            "interactable": obj.interactable,
        }
        for obj in objects
    ]


def _build_pc_ctx(pc: PlayerCharacter, positions: dict[str, dict[str, int]]) -> dict[str, Any]:
    pos = positions.get(pc.id, {"x": pc.position_x, "y": pc.position_y})
    return {
        "id": pc.id,
        "name": pc.name,
        "role": pc.role,
        "race": pc.race or "",
        "status": pc.status,
        "position_x": pos["x"],
        "position_y": pos["y"],
    }


def _build_actor_ctx(actors: list) -> list[dict[str, Any]]:
    return [
        {
            "id": actor.id,
            "name": actor.name,
            "role": actor.role,
            "race": actor.race or "",
            "status": actor.status,
            "position_x": actor.position_x,
            "position_y": actor.position_y,
            "personality": actor.personality,
            "disposition": actor.disposition,
        }
        for actor in actors
    ]
