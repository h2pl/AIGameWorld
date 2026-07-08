"""DM Engine——LLM 驱动的情境创造与叙事。per design/04-agent-layer.md §5.

分层遵循 Service → Engine → Repository 调用链：
Service 负责 State↔Request 适配，Engine 负责业务逻辑 + 从 config 取 repos 调用 Repository。
"""

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

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
) -> dict:
    """Phase 1: DM 创造情境 / DM creates situation."""
    llm = get_llm(config)
    if llm is None:
        raise RuntimeError("[dm_create] LLM client not configured")

    scene_repo = get_repo(config, "scene")
    scenes: list[dict] = []
    scene_objects_by_scene: dict[str, list[dict]] = {}
    if scene_repo and world_id:
        raw_scenes = await scene_repo.list_scenes(world_id)
        all_objects = await scene_repo.list_objects_by_world(world_id)
        for obj in all_objects:
            scene_objects_by_scene.setdefault(obj.get("scene_id", ""), []).append(obj)
        scenes = [
            _enrich_scene(s.model_dump(), scene_objects_by_scene.get(s.id, [])) for s in raw_scenes
        ]

    # 检索 DM 记忆（复用 dm_records）/ Retrieve DM memories from dm_records
    memories: list[str] = []
    try:
        mems = await retrieve_dm_records(
            world_id or "", config=config, top_k=5, before_tick=tick
        )
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

    return {
        "hints": result.hints,
        "plot_brief": result.plot_brief,
        "scene_id": result.scene_id,
        "ext": result.model_dump(),
    }


async def dm_narrate(
    tick: int,
    world_id: str,
    plot_brief: str,
    hints: list[str],
    events: list,
    scene: dict,
    scene_objects: list[dict],
    pcs: dict,
    actors: dict,
    actions: list[dict],
    config: RunnableConfig = None,
) -> str:
    """Phase 6: DM 叙事 / DM narrates.

    注意：本函数不再提供 fallback 叙事。LLM 返回空视为后端/模型异常，
    必须抛出并记录完整上下文，方便排查根因。
    """
    llm = get_llm(config)
    if llm is None:
        raise RuntimeError("[dm_narrate] LLM client not configured")

    # 检索 DM 记忆（复用 dm_records）/ Retrieve DM memories from dm_records
    dm_memories: list[str] = []
    try:
        mems = await retrieve_dm_records(
            world_id or "", config=config, top_k=3, before_tick=tick
        )
        dm_memories = list(mems) if mems else []
    except Exception:
        logger.warning("[engine] dm_narrate memory retrieval failed, continuing without memories")

    # actions.result 可能是 Pydantic 模型，模板用 dict.get，需要统一转 dict
    normalized_actions = _normalize_actions(actions)

    system_prompt = await _render_dm_system(config, world_id)
    prompt = _PROMPTS.get_template("dm/dm_narrate.jinja").render(
        tick=tick,
        plot_brief=plot_brief,
        hints=hints,
        scene=scene,
        scene_objects=scene_objects,
        pcs=list(pcs.values()),
        actors=list(actors.values()),
        events=events,
        actions=normalized_actions,
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
            tick, prompt[:1200],
        )
        raise RuntimeError(
            f"[dm_narrate] LLM returned empty narrative at tick={tick}"
        )

    logger.info("[engine] dm_narrate tick=%s narrative_len=%s", tick, len(narrative))
    return narrative


def _normalize_actions(actions: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """把 action.result 中的 Pydantic/对象统一转成 dict，供模板安全使用 / Normalize action results to dicts."""
    if not actions:
        return []
    normalized: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            normalized.append({"raw": str(action)[:200]})
            continue
        item = dict(action)
        result = item.get("result")
        if hasattr(result, "model_dump"):
            item["result"] = result.model_dump()
        elif hasattr(result, "__dict__"):
            item["result"] = {k: v for k, v in result.__dict__.items() if not k.startswith("_")}
        normalized.append(item)
    return normalized


async def _render_dm_system(config: RunnableConfig | None, world_id: str) -> str:
    """渲染 DM system prompt，注入世界观信息 / Render DM system prompt with world info."""
    world = None
    if world_id:
        world_repo = get_repo(config, "world")
        if world_repo:
            w = await world_repo.get(world_id)
            if w:
                world = {"name": w.name, "description": w.description, "rule_set": w.rule_set}
    return _PROMPTS.get_template("dm/_dm_system.jinja").render(world=world)


def _enrich_scene(scene: dict, objects: list[dict]) -> dict:
    """解析 ext_json 并补充场景物体信息 / Parse ext_json and attach scene objects."""
    ext = {}
    ext_json = scene.get("ext_json", "{}")
    if isinstance(ext_json, str) and ext_json.strip():
        try:
            ext = json.loads(ext_json)
        except json.JSONDecodeError:
            ext = {}
    return {
        "id": scene.get("id", ""),
        "name": scene.get("name", ""),
        "type": scene.get("type", ""),
        "description": scene.get("description", ""),
        "spawn_x": scene.get("spawn_x", 0),
        "spawn_y": scene.get("spawn_y", 0),
        "map_width": scene.get("map_width", 40),
        "map_height": scene.get("map_height", 40),
        "tilemap_summary": scene.get("tilemap_summary", ""),
        "environment": ext.get("environment", {}),
        "objects": objects,
    }
