"""PC Decision Engine——LLM 驱动的单个 PC 决策 / LLM-driven single PC decision.

暂不支持配角（Actor）的主动行为 / NPC proactive behavior not yet supported.
"""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ...schemas.llm_output import CharacterActionSchema
from ...schemas.response import PCDecideResponse
from ...utils.helpers import get_llm, get_repo

logger = logging.getLogger("aw.eng.char")

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))
_VALID_ACTIONS = {"move", "talk", "attack", "interact", "wait"}


async def decide(
    observation: dict,
    plot_brief: str,
    hints: list[str],
    scene_id: str,
    tick: int,
    config: RunnableConfig = None,
) -> dict | None:
    """基于单个 PC 的场景观察结果决策 / Decide from a single PC scene observation."""
    pc_id = observation.get("pc_id", "")
    logger.info("[character] tick=%s processing pc %s", tick, pc_id)

    llm = get_llm(config)
    if llm is None:
        return PCDecideResponse(
            pc_id=pc_id,
            type="wait",
            description="等待时机。",
            errors=["LLM 不可用，使用降级输出 / LLM unavailable, fallback used"],
        ).model_dump()

    try:
        scene = await _fetch_scene(scene_id, config)
        scene_objects = await _fetch_scene_objects(observation.get("scene_object_ids", []), config)
        nearby_pcs = await _fetch_nearby_pcs(observation.get("nearby_pc_ids", []), config)
        nearby_actors = await _fetch_nearby_actors(observation.get("nearby_actor_ids", []), config)

        ctx = {
            "plot_brief": plot_brief,
            "hints": hints,
            "scene": _build_scene_ctx(scene, scene_id),
            "scene_objects": _build_scene_object_ctx(scene_objects),
            "nearby_pcs": _build_pc_ctx(nearby_pcs),
            "nearby_actors": _build_actor_ctx(nearby_actors),
        }
        system = _PROMPTS.get_template("_pc_system.jinja").render(**ctx)
        try:
            prompt = _PROMPTS.get_template("decide/pc_decide.jinja").render(**ctx)
        except Exception:
            prompt = f"Plot brief: {plot_brief}\nRespond with the next action."
        result = await llm.call_structured(
            "pc_decision",
            CharacterActionSchema,
            [SystemMessage(content=system), HumanMessage(content=prompt)],
            fallback=lambda: CharacterActionSchema(action_type="wait", reasoning="LLM 降级。"),
        )
        result = _validate(result)
        return PCDecideResponse(
            pc_id=pc_id, type=result.action_type, description=result.reasoning
        ).model_dump()
    except Exception:
        logger.exception("[character] failed for pc %s", pc_id)
        return PCDecideResponse(
            pc_id=pc_id,
            type="wait",
            description="等待时机。",
            errors=["pc_decide LLM 调用失败，使用降级输出"],
        ).model_dump()


# ── 查询 Repo / Repo queries（只负责取数据，不做组装）──


async def _fetch_scene(scene_id: str, config: RunnableConfig = None) -> dict | None:
    """按 scene_id 查询场景 / Fetch scene by id."""
    scene_repo = get_repo(config, "scene")
    if not scene_repo or not scene_id:
        return None
    return await scene_repo.get_scene(scene_id)


async def _fetch_scene_objects(object_ids: list[str], config: RunnableConfig = None) -> list:
    """按 id 列表查询场景物体 / Fetch scene objects by ids."""
    scene_repo = get_repo(config, "scene")
    if not scene_repo or not object_ids:
        return []
    all_objects = await scene_repo.load_all()
    return [all_objects[oid] for oid in object_ids if oid in all_objects]


async def _fetch_nearby_pcs(pc_ids: list[str], config: RunnableConfig = None) -> list:
    """按 id 列表查询附近 PC / Fetch nearby PCs by ids."""
    char_repo = get_repo(config, "char")
    if not char_repo:
        return []
    pcs = [await char_repo.load_pc(pid) for pid in pc_ids]
    return [pc for pc in pcs if pc]


async def _fetch_nearby_actors(actor_ids: list[str], config: RunnableConfig = None) -> list:
    """按 id 列表查询附近 Actor / Fetch nearby actors by ids."""
    char_repo = get_repo(config, "char")
    if not char_repo:
        return []
    actors = [await char_repo.load_actor(aid) for aid in actor_ids]
    return [a for a in actors if a]


# ── 组装 Prompt Context / Assemble prompt context（只做数据转换，不查 repo）──


def _build_scene_ctx(scene: dict | None, scene_id: str) -> dict:
    if not scene:
        return {
            "id": scene_id,
            "name": "",
            "type": "",
            "description": "",
            "landmarks": [],
            "exits": [],
        }
    return {
        "id": scene.get("id", scene_id),
        "name": scene.get("name", ""),
        "type": scene.get("type", ""),
        "description": scene.get("description", ""),
        "landmarks": scene.get("landmarks", []),
        "exits": scene.get("exits", []),
    }


def _build_scene_object_ctx(objects: list) -> list[dict]:
    return [
        {
            "name": obj.name,
            "object_type": obj.object_type.value,
            "interactable": obj.interactable,
        }
        for obj in objects
    ]


def _build_pc_ctx(pcs: list) -> list[dict]:
    return [
        {
            "name": pc.name,
            "role": pc.role,
            "race": pc.race or "",
            "status": pc.status,
        }
        for pc in pcs
    ]


def _build_actor_ctx(actors: list) -> list[dict]:
    return [
        {
            "name": actor.name,
            "role": actor.role,
            "race": actor.race or "",
            "status": actor.status,
            "personality": actor.personality,
            "disposition": actor.disposition,
        }
        for actor in actors
    ]


def _validate(result: CharacterActionSchema) -> CharacterActionSchema:
    if result.action_type not in _VALID_ACTIONS:
        result.action_type = "wait"
    if not result.reasoning or not result.reasoning.strip():
        result.reasoning = "等待时机。"
    return result
