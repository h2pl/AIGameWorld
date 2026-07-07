"""Scene Service: State ↔ Engine adapter.

负责在 tick 开始时构建场景相关的领域模型并写入 state：
- scene: 单场景信息 dict
- scene_objects: 场景物体 list
- actors: Actor 领域模型 map
- pcs: PlayerCharacter 领域模型 map

使用领域模型而非 model_dump 后的 dict，方便各节点直接读写全量信息，
也便于 data_service 在 tick 末尾直接 save() 落盘。
"""

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ..domain import Actor, PlayerCharacter, Scene, SceneObject, SceneObjectType
from ..graph.state import OverallState
from ..schemas.llm_output import (
    ActorGenerationSchema,
    SceneObjectGenerationSchema,
    TilemapInterpretationSchema,
)
from ..utils.helpers import build_occupied_set, find_vacant_adjacent, get_llm, get_repo
from ..utils.logging import get_logger, trace_node

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(str(_PROMPTS_ROOT)))


@trace_node("scene.build_scene_state")
async def build_scene_state(state: OverallState, config=None) -> dict:
    """Phase 1.5: 顺序调用 6 个场景方法，构建完整场景信息 / Sequential wrapper."""
    tick = state.get("tick", 0)
    scene_id = state.get("scene_id", "")
    logger.info("[service] tick=%s scene_id=%s", tick, scene_id)

    result: dict[str, Any] = {}
    result.update(await build_scene_info(state, config))
    result.update(await interpret_tilemap({**state, **result}, config))
    result.update(await generate_actors({**state, **result}, config))
    result.update(await build_actors({**state, **result}, config))
    result.update(await build_pcs({**state, **result}, config))
    result.update(await generate_scene_objects({**state, **result}, config))
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


@trace_node("scene.interpret_tilemap")
async def interpret_tilemap(
    state: OverallState,
    config: RunnableConfig = None,
    assets_dir: Path | None = None,
) -> dict:
    """动态生成 tilemap 语义摘要：scene 无摘要时，读取 tilemap 文件并调用 LLM 生成。"""
    scene_id = state.get("scene_id", "")
    scene = state.get("scene")
    if scene is None:
        return {"scene": scene}

    if scene.tilemap_summary:
        logger.info("[scene] %s tilemap_summary exists, skip interpretation", scene_id)
        return {"scene": scene}

    scene_repo = get_repo(config, "scene")
    if scene_repo is None:
        return {"scene": scene}

    tilemap = _load_tilemap(scene, assets_dir=assets_dir)
    if tilemap is None:
        logger.warning("[scene] no tilemap found for %s", scene_id)
        return {"scene": scene}

    llm = get_llm(config)
    if llm is None:
        logger.warning("[scene] LLM unavailable, cannot interpret tilemap for %s", scene_id)
        return {"scene": scene}

    # 压缩 tilemap 元数据，避免向 LLM 发送完整 data 数组 / Compress tilemap metadata for LLM
    compact = _summarize_tilemap(tilemap)
    ctx = {
        "scene": scene,
        "tilemap": compact,
        "plot_brief": state.get("plot_brief", ""),
        "hints": state.get("hints", []),
    }
    system = _PROMPTS.get_template("tilemap/_interpret_system.jinja").render(**ctx)
    prompt = _PROMPTS.get_template("tilemap/interpret.jinja").render(**ctx)

    # 调用 LLM 生成语义摘要 / Ask LLM for semantic summary
    result = await llm.call_structured(
        "interpret_tilemap",
        TilemapInterpretationSchema,
        [SystemMessage(content=system), HumanMessage(content=prompt)],
    )
    summary = result.summary.strip()
    if summary:
        await scene_repo.save_tilemap_summary(scene_id, summary)
        logger.info("[scene] interpreted tilemap for %s", scene_id)
        scene.tilemap_summary = summary
    return {"scene": scene}


@trace_node("scene.generate_actors")
async def generate_actors(state: OverallState, config: RunnableConfig = None) -> dict:
    """动态生成 Actor：当前场景无 NPC 时，调用 LLM 生成并入库。"""
    scene_id = state.get("scene_id", "")
    world_id = state.get("world_id", "")
    if not scene_id or not world_id:
        return {"_generated_actors": []}

    actor_repo = get_repo(config, "actor")
    if actor_repo is None:
        return {"_generated_actors": []}

    existing = await actor_repo.load_all(world_id)
    scene_actors = [a for a in existing if getattr(a, "scene_id", "") == scene_id]
    if scene_actors:
        logger.info(
            "[scene] %s already has %d actors, skip generation", scene_id, len(scene_actors)
        )
        return {"_generated_actors": []}

    llm = get_llm(config)
    if llm is None:
        logger.warning("[scene] LLM unavailable, cannot generate actors for %s", scene_id)
        return {"_generated_actors": []}

    scene = state.get("scene")
    if scene is None:
        return {"_generated_actors": []}
    ctx = _build_spawn_ctx(scene, state)
    system = _PROMPTS.get_template("spawn/_actor_spawn_system.jinja").render(**ctx)
    prompt = _PROMPTS.get_template("spawn/actor_spawn.jinja").render(**ctx)

    result = await llm.call_structured(
        "spawn_actors",
        ActorGenerationSchema,
        [SystemMessage(content=system), HumanMessage(content=prompt)],
    )

    generated: list[Actor] = []
    occupied: set[tuple[int, int]] = set()  # 已占用坐标 / Occupied coordinates
    map_width = ctx["map_width"]
    map_height = ctx["map_height"]
    for raw in result.actors:
        # 裁剪到地图范围并去重 / Clamp to map bounds and avoid overlap
        x = max(0, min(map_width - 1, raw.position_x))
        y = max(0, min(map_height - 1, raw.position_y))
        if (x, y) in occupied:
            x, y = find_vacant_adjacent(x, y, occupied, map_width, map_height)
        occupied.add((x, y))

        # 构造 Actor 领域模型并入库 / Build Actor domain model and persist
        actor = Actor(
            id=raw.id,
            name=raw.name,
            role=raw.role,
            race=raw.race,
            disposition=raw.disposition,
            status=raw.status,
            personality=raw.personality,
            scene_id=scene_id,
            position_x=x,
            position_y=y,
            attributes_json=raw.attributes_json,
            combat_json=raw.combat_json,
            world_id=world_id,
        )
        await actor_repo.save(actor)
        generated.append(actor)

    logger.info("[scene] generated %d actors for %s", len(generated), scene_id)
    return {"_generated_actors": [a.id for a in generated]}


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


@trace_node("scene.generate_scene_objects")
async def generate_scene_objects(state: OverallState, config: RunnableConfig = None) -> dict:
    """动态生成场景物体：当前场景无物体时，调用 LLM 生成并入库。"""
    scene_id = state.get("scene_id", "")
    world_id = state.get("world_id", "")
    if not scene_id or not world_id:
        return {"_generated_scene_objects": []}

    scene_repo = get_repo(config, "scene")
    if scene_repo is None:
        return {"_generated_scene_objects": []}

    object_ids = await scene_repo.get_object_ids(scene_id)
    if object_ids:
        logger.info("[scene] %s already has %d objects, skip generation", scene_id, len(object_ids))
        return {"_generated_scene_objects": []}

    llm = get_llm(config)
    if llm is None:
        logger.warning("[scene] LLM unavailable, cannot generate scene objects for %s", scene_id)
        return {"_generated_scene_objects": []}

    scene = state.get("scene")
    if scene is None:
        return {"_generated_scene_objects": []}
    ctx = _build_spawn_ctx(scene, state)
    system = _PROMPTS.get_template("spawn/_object_spawn_system.jinja").render(**ctx)
    prompt = _PROMPTS.get_template("spawn/object_spawn.jinja").render(**ctx)

    result = await llm.call_structured(
        "spawn_objects",
        SceneObjectGenerationSchema,
        [SystemMessage(content=system), HumanMessage(content=prompt)],
    )

    actors = state.get("actors", {})
    occupied = build_occupied_set(None, actors, exclude_id="")
    map_width = ctx["map_width"]
    map_height = ctx["map_height"]

    generated: list[SceneObject] = []
    for raw in result.objects:
        # 裁剪坐标并避开 Actor 已占位置 / Clamp coords and avoid actor positions
        x = max(0, min(map_width - 1, raw.position_x))
        y = max(0, min(map_height - 1, raw.position_y))
        if (x, y) in occupied:
            x, y = find_vacant_adjacent(x, y, occupied, map_width, map_height)
        occupied.add((x, y))

        # 非法 object_type 降级为 decoration / Fallback unknown type to decoration
        try:
            obj_type = SceneObjectType(raw.object_type)
        except ValueError:
            obj_type = SceneObjectType.DECORATION

        # 构造 SceneObject 领域模型并入库 / Build SceneObject domain model and persist
        obj = SceneObject(
            id=raw.id,
            name=raw.name,
            object_type=obj_type,
            scene_id=scene_id,
            position_x=x,
            position_y=y,
            interactable=raw.interactable,
            interact_data=raw.interact_data,
            world_id=world_id,
        )
        await scene_repo.save_object(obj)
        generated.append(obj)

    logger.info("[scene] generated %d scene objects for %s", len(generated), scene_id)
    return {"_generated_scene_objects": [o.id for o in generated]}


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

    from ..utils.helpers import build_occupied_set, find_vacant_adjacent

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


def _build_spawn_ctx(scene: Scene, state: OverallState) -> dict[str, Any]:
    """构建生成 prompt 上下文 / Build spawn prompt context."""
    actors = state.get("actors", {})
    scene_objects = state.get("scene_objects", [])
    return {
        "scene": scene,
        "plot_brief": state.get("plot_brief", ""),
        "hints": state.get("hints", []),
        "map_width": scene.map_width,
        "map_height": scene.map_height,
        "spawn_x": scene.spawn_x,
        "spawn_y": scene.spawn_y,
        "existing_actors": list(actors.values()),
        "existing_objects": scene_objects,
    }


def _build_scene_object_ctx(objects: list) -> list[dict[str, Any]]:
    return [
        {
            "id": obj.id,
            "name": obj.name,
            "object_type": obj.object_type.value,
            "scene_id": getattr(obj, "scene_id", ""),
            "interactable": obj.interactable,
            "position_x": obj.position_x,
            "position_y": obj.position_y,
            "interact_data": obj.interact_data or {},
        }
        for obj in objects
    ]


def _default_assets_dir() -> Path:
    """默认 tilemap 资源目录：backend 的 sibling frontend/public/assets."""
    backend_root = Path(__file__).parent.parent.parent
    return backend_root.parent / "frontend" / "public" / "assets"


def _load_tilemap(scene: Scene, assets_dir: Path | None = None) -> dict | None:
    """根据 scene.id / ext_json.tilemap_url 读取 tilemap JSON 文件。"""
    assets_dir = assets_dir or _default_assets_dir()
    if not assets_dir.exists():
        return None

    ext_json = scene.ext_json
    try:
        ext = json.loads(ext_json) if ext_json else {}
    except json.JSONDecodeError:
        ext = {}

    # 优先使用 ext_json.tilemap_url，否则回退到 scene_id.json / Prefer tilemap_url, fallback to scene_id.json
    tilemap_url = ext.get("tilemap_url", "")
    if tilemap_url:
        filename = tilemap_url.lstrip("/").split("/")[-1]  # /assets/foo.json → foo.json
        path = assets_dir / filename
    else:
        path = assets_dir / f"{scene.id}.json"

    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _summarize_tilemap(tilemap: dict[str, Any]) -> str:
    """把 tilemap JSON 压缩成 LLM 可读的文本摘要（不发送完整 data 数组）。"""
    # 只统计每层非空 tile 数量，不暴露完整 data / Count non-empty tiles per layer, omit full data
    layers = tilemap.get("layers", [])
    layer_infos = []
    for layer in layers:
        data = layer.get("data", [])
        non_empty = [v for v in data if v]
        layer_infos.append(
            f"- {layer.get('name', 'unnamed')}: type={layer.get('type', '')}, "
            f"visible={layer.get('visible', True)}, non_empty_tiles={len(non_empty)}"
        )

    # 提取图集元数据 / Extract tileset metadata
    tilesets = tilemap.get("tilesets", [])
    tileset_infos = [
        f"- {ts.get('name', 'unnamed')}: image={ts.get('image', '')}, tile={ts.get('tilewidth', 0)}x{ts.get('tileheight', 0)}"
        for ts in tilesets
    ]

    props = tilemap.get("properties", {})
    prop_info = f"自定义属性: {props}" if props else "自定义属性: 无"

    return (
        f"地图尺寸: {tilemap.get('width', 0)}x{tilemap.get('height', 0)}, "
        f"tile 尺寸: {tilemap.get('tilewidth', 0)}x{tilemap.get('tileheight', 0)}\n"
        f"方向: {tilemap.get('orientation', 'orthogonal')}\n"
        "图层:\n" + "\n".join(layer_infos) + "\n"
        "图集:\n" + "\n".join(tileset_infos) + "\n"
        f"{prop_info}"
    )
