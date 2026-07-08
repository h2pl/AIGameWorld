"""DM Engine——LLM 驱动的情境创造与叙事。per design/04-agent-layer.md §5.

分层遵循 Service → Engine → Repository 调用链：
Service 负责 State↔Request 适配，Engine 负责业务逻辑 + 从 config 取 repos 调用 Repository。
"""

import json
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ...domain import (
    Action,
    Actor,
    DMRecord,
    PlayerCharacter,
    Scene,
    SceneObject,
    TickEvent,
    World,
)
from ...schemas.llm_output import DMNarrativeSchema, DMOutput
from ...services.memory_service import retrieve_dm_records
from ...utils.helpers import get_llm, get_repo
from ...utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))


async def dm_create(
    tick: int,
    world_id: str = "",
    plot_brief: str = "",
    config: RunnableConfig = None,
) -> DMRecord:
    """Phase 1: DM 创造情境 / DM creates situation."""
    llm = get_llm(config)
    if llm is None:
        raise RuntimeError("[dm_create] LLM client not configured")

    scene_repo = get_repo(config, "scene")
    scenes: list[SimpleNamespace] = []
    scene_objects_by_scene: dict[str, list[SceneObject]] = {}
    if scene_repo and world_id:
        raw_scenes = await scene_repo.list_scenes(world_id)
        all_objects = await scene_repo.list_objects_by_world(world_id)
        for obj in all_objects:
            scene_obj = SceneObject(**obj)
            scene_objects_by_scene.setdefault(scene_obj.scene_id, []).append(scene_obj)
        scenes = [_enrich_scene(s, scene_objects_by_scene.get(s.id, [])) for s in raw_scenes]

    # 检索 DM 记忆（复用 dm_records）/ Retrieve DM memories from dm_records
    memories: list[str] = []
    try:
        mems = await retrieve_dm_records(world_id or "", config=config, top_k=5, before_tick=tick)
        memories = list(mems) if mems else []
    except Exception:
        logger.warning("[engine] dm_create memory retrieval failed, continuing without memories")

    logger.info("[engine] dm_create tick=%s world=%s", tick, world_id or "-")
    system_prompt = await _render_dm_system(config, world_id)
    prompt = _PROMPTS.get_template("dm/dm_create.jinja").render(
        scenes=scenes,
        recent_summary="",
        plot_brief_prev=plot_brief,
        memories=memories,
        pacing={},
    )
    result = await llm.call_structured(
        "dm_create",
        DMOutput,
        [SystemMessage(content=system_prompt), HumanMessage(content=prompt)],
    )
    if len(result.hints) > 4:
        result.hints = result.hints[:4]

    return DMRecord(
        world_id=world_id,
        tick=tick,
        plot_brief=result.plot_brief,
        hints=result.hints,
        scene_id=result.scene_id,
        ext=result.model_dump(),
    )


async def dm_narrate(
    tick: int,
    world_id: str,
    plot_brief: str,
    hints: list[str],
    events: list[TickEvent],
    scene: Scene,
    scene_objects: list[SceneObject],
    pcs: dict[str, PlayerCharacter],
    actors: dict[str, Actor],
    actions: list[Action],
    config: RunnableConfig = None,
) -> str:
    """Phase 6: DM 叙事 / DM narrates."""
    llm = get_llm(config)
    if llm is None:
        raise RuntimeError("[dm_narrate] LLM client not configured")

    # 检索 DM 记忆（复用 dm_records）
    dm_memories: list[str] = []
    try:
        mems = await retrieve_dm_records(world_id or "", config=config, top_k=3, before_tick=tick)
        dm_memories = list(mems) if mems else []
    except Exception:
        logger.warning("[engine] dm_narrate memory retrieval failed, continuing without memories")

    system_prompt = await _render_dm_system(config, world_id)
    prompt = _PROMPTS.get_template("dm/dm_narrate.jinja").render(
        tick=tick,
        plot_brief=plot_brief,
        hints=hints,
        scene=scene,
        scene_objects=scene_objects,
        pcs=list(pcs.values()),
        actors=list(actors.values()),
        events=_event_summaries(events),
        actions=actions,
        memories=dm_memories,
    )

    result = await llm.call_structured(
        "dm_narrate",
        DMNarrativeSchema,
        [SystemMessage(content=system_prompt), HumanMessage(content=prompt)],
    )

    narrative = (result.narrative or "").strip()
    if not narrative:
        logger.error(
            "[engine] dm_narrate produced empty narrative; tick=%s prompt_preview=%s",
            tick,
            prompt[:1200],
        )
        raise RuntimeError(f"[dm_narrate] LLM returned empty narrative at tick={tick}")

    logger.info("[engine] dm_narrate tick=%s narrative_len=%s", tick, len(narrative))
    return narrative


def _event_summaries(events: list[TickEvent] | None) -> list[str]:
    """把 TickEvent 列表转成 prompt 可读的摘要 / Summarize events for prompt."""
    summaries: list[str] = []
    for ev in events or []:
        ev_type = ev.type.value if hasattr(ev.type, "value") else str(ev.type)
        payload = ev.payload
        description = str(payload)[:200] if payload else ""
        summaries.append(f"{ev_type}：{description}")
    return summaries


async def _render_dm_system(config: RunnableConfig | None, world_id: str) -> str:
    """渲染 DM system prompt，注入世界观信息 / Render DM system prompt with world info."""
    world: World | None = None
    if world_id:
        world_repo = get_repo(config, "world")
        if world_repo:
            world = await world_repo.get(world_id)
    return _PROMPTS.get_template("dm/_dm_system.jinja").render(world=world)


def _enrich_scene(scene: Scene, objects: list[SceneObject]) -> SimpleNamespace:
    """解析 ext_json 并补充场景物体信息 / Parse ext_json and attach scene objects."""
    ext: dict = {}
    if isinstance(scene.ext_json, str) and scene.ext_json.strip():
        try:
            ext = json.loads(scene.ext_json)
        except json.JSONDecodeError:
            ext = {}
    return SimpleNamespace(
        id=scene.id,
        name=scene.name,
        type=scene.type,
        description=scene.description,
        spawn_x=scene.spawn_x,
        spawn_y=scene.spawn_y,
        map_width=scene.map_width,
        map_height=scene.map_height,
        tilemap_summary=scene.tilemap_summary,
        environment=ext.get("environment", {}),
        objects=objects,
    )
