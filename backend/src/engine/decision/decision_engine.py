"""PC Decision Engine——LLM 驱动的单个 PC 多行动决策 / LLM-driven multi-action PC decision."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ...schemas.llm_output import CharacterActionSchema, PCDecideListSchema
from ...schemas.response import PCDecideResponse
from ...services.memory_service import retrieve_memories
from ...utils.helpers import get_llm
from ...utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))
_VALID_ACTIONS = {"talk", "interact", "combat", "explore", "wait"}
_ACTION_TARGET_TYPES = {
    "talk": {"pc", "actor"},
    "interact": {"scene_object"},
    "combat": {"pc", "actor"},
}


async def decide(
    pc_id: str,
    scene_info: dict,
    plot_brief: str,
    hints: list[str],
    scene_id: str,
    tick: int,
    pc_state_map: dict[str, dict] | None = None,
    actor_state_map: dict[str, dict] | None = None,
    config: RunnableConfig = None,
) -> list[dict]:
    """为单个 PC 决策 / Decide for a PC, return 1-3 actions.

    PC/Actor 身份和坐标统一从 pc_state_map / actor_state_map 读取（tick 内权威数据源）。
    """
    logger.info("[engine] decide tick=%s pc=%s", tick, pc_id or "-")

    llm = get_llm(config)
    if llm is None:
        raise RuntimeError("[decide] LLM client not configured")
    pc_map = pc_state_map or {}

    # 从 state map 读当前 PC 身份 / Read current PC identity from state map
    me = _map_identity(pc_id, pc_map)
    # 同场景其他 PC / Other PCs in scene
    nearby_pcs = [_map_identity(pid, pc_map) for pid in pc_map if pid != pc_id]
    # 同场景 Actor / Actors in scene
    actor_map = actor_state_map or {}
    nearby_actors = [_map_identity(aid, actor_map) for aid in actor_map]

    query = f"{plot_brief} {scene_info.get('scene', {}).get('description', '')}".strip()
    memories = await retrieve_memories(pc_id, query, config=config, top_k=5)

    ctx = {
        "me": me,
        "plot_brief": plot_brief,
        "hints": hints,
        "memories": memories,
        "scene": scene_info.get("scene")
        or {
            "id": scene_id,
            "name": "",
            "type": "",
            "description": "",
            "landmarks": [],
            "exits": [],
        },
        "scene_objects": scene_info.get("scene_objects", []),
        "nearby_pcs": nearby_pcs,
        "nearby_actors": nearby_actors,
    }
    system = _PROMPTS.get_template("decide/_pc_system.jinja").render(**ctx)
    prompt = _PROMPTS.get_template("decide/pc_decide.jinja").render(**ctx)

    result = await llm.call_structured(
        "pc_decision",
        PCDecideListSchema,
        [SystemMessage(content=system), HumanMessage(content=prompt)],
    )

    decisions: list[dict] = []
    for action in result.actions:
        validated = _validate(action, scene_info, pc_map, actor_map)
        decisions.append(
            PCDecideResponse(
                pc_id=pc_id,
                type=validated.action_type,
                target_id=validated.target_id,
                target_type=validated.target_type,
                description=validated.reasoning,
            ).model_dump()
        )
    if not decisions:
        decisions = [_fallback_decision(pc_id)]
    return decisions


def _fallback_decision(pc_id: str) -> dict:
    return PCDecideResponse(
        pc_id=pc_id,
        type="wait",
        description="等待时机。",
    ).model_dump()


def _map_identity(char_id: str, state_map: dict[str, dict]) -> dict:
    """从 state map 读取角色身份 / Read character identity from state map."""
    info = state_map.get(char_id, {})
    return {
        "id": char_id,
        "name": info.get("name", char_id),
        "role": info.get("role", ""),
        "personality": info.get("personality", ""),
    }


def _validate(
    result: CharacterActionSchema,
    scene_info: dict | None = None,
    pc_state_map: dict[str, dict] | None = None,
    actor_state_map: dict[str, dict] | None = None,
) -> CharacterActionSchema:
    """校验并修正 LLM 返回的动作 / Validate LLM action, fallback to wait for invalid combos."""
    if result.action_type not in _VALID_ACTIONS:
        result.action_type = "wait"
    if result.action_type in ("wait", "explore"):
        result.target_id = None
        result.target_type = None
    else:
        allowed_types = _ACTION_TARGET_TYPES.get(result.action_type, set())
        if not result.target_id or result.target_type not in allowed_types:
            result.action_type = "wait"
            result.target_id = None
            result.target_type = None
        elif not _target_in_scene(
            result.target_id, result.target_type, scene_info, pc_state_map, actor_state_map
        ):
            logger.warning(
                "[engine] target %s (%s) not in scene, downgrading to wait",
                result.target_id,
                result.target_type,
            )
            result.action_type = "wait"
            result.target_id = None
            result.target_type = None
    if not result.reasoning or not result.reasoning.strip():
        result.reasoning = "等待时机。"
    return result


def _target_in_scene(
    target_id: str,
    target_type: str,
    scene_info: dict | None = None,
    pc_state_map: dict[str, dict] | None = None,
    actor_state_map: dict[str, dict] | None = None,
) -> bool:
    """检查目标是否在当前场景 / Check if target exists in current scene."""
    if target_type == "scene_object":
        objects = (scene_info or {}).get("scene_objects", [])
        return any(o.get("id") == target_id for o in objects)
    if target_type == "pc":
        return target_id in (pc_state_map or {})
    if target_type == "actor":
        return target_id in (actor_state_map or {})
    return False
