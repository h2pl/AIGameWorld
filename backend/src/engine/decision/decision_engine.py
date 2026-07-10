"""PC Decision Engine——LLM 驱动的单个 PC 多行动决策 / LLM-driven multi-action PC decision."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from src.utils.tracing import traced

from ...domain import Actor, Decision, DMRecord, PlayerCharacter, Scene, SceneObject
from ...schemas.llm_output import CharacterActionSchema, PCDecideSchema
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


@traced()
async def decide(
    pc_id: str,
    tick: int,
    scene: Scene | None = None,
    scene_objects: list[SceneObject] | None = None,
    pcs: dict[str, PlayerCharacter] | None = None,
    actors: dict[str, Actor] | None = None,
    dm_record: DMRecord | None = None,
    config: RunnableConfig = None,
) -> Decision:
    """为单个 PC 决策 / Decide for a PC, return exactly one action.

    PC/Actor 身份和坐标统一从 pcs / actors 读取（tick 内权威数据源）。
    """
    logger.info("[engine] decide tick=%s pc=%s", tick, pc_id or "-")

    llm = get_llm(config)
    if llm is None:
        raise RuntimeError("[decide] LLM client not configured")
    pcs = pcs or {}
    actors = actors or {}

    plot_brief = dm_record.plot_brief if dm_record else ""
    hints = dm_record.hints if dm_record else []

    # 从领域模型 map 读当前 PC 身份 / Read current PC identity from domain model map
    me = _map_identity(pcs.get(pc_id))
    # 同场景其他 PC / Other PCs in scene
    nearby_pcs = [_map_identity(pcs[pid]) for pid in pcs if pid != pc_id]
    # 同场景 Actor / Actors in scene
    nearby_actors = [_map_identity(actors[aid]) for aid in actors]

    query = f"{plot_brief} {scene.description if scene else ''}".strip()
    memories = await retrieve_memories(pc_id, query, config=config, top_k=5)

    ctx = {
        "me": me,
        "plot_brief": plot_brief,
        "hints": hints,
        "memories": memories,
        "scene": scene
        or {
            "id": scene.id if scene else (dm_record.scene_id if dm_record else ""),
            "name": "",
            "type": "",
            "description": "",
            "tilemap_summary": "",
        },
        "scene_objects": scene_objects or [],
        "nearby_pcs": nearby_pcs,
        "nearby_actors": nearby_actors,
    }
    system = _PROMPTS.get_template("decide/_pc_system.jinja").render(**ctx)
    prompt = _PROMPTS.get_template("decide/pc_decide.jinja").render(**ctx)

    result = await llm.call_structured(
        "pc_decision",
        PCDecideSchema,
        [SystemMessage(content=system), HumanMessage(content=prompt)],
    )

    validated = _validate(result.action, scene, scene_objects, pcs, actors)
    return Decision(
        pc_id=pc_id,
        type=validated.action_type,
        target_id=validated.target_id,
        target_type=validated.target_type,
        thought=validated.thought,
        description=validated.thought,  # thought 即决策理由 / thought IS the rationale
        explore_x=validated.explore_x,
        explore_y=validated.explore_y,
    )


def _fallback_decision(pc_id: str) -> Decision:
    return Decision(
        pc_id=pc_id,
        type="wait",
        thought="当前没有明确目标，先观察局势。",
        description="当前没有明确目标，先观察局势。",
    )


def _map_identity(char: PlayerCharacter | Actor | None) -> dict:
    """从领域模型读取角色身份 / Read character identity from domain model."""
    if char is None:
        return {
            "id": "",
            "name": "",
            "role": "",
            "race": "",
            "status": "active",
            "personality": "",
            "disposition": "neutral",
        }
    return {
        "id": char.id,
        "name": char.name,
        "role": getattr(char, "role", ""),
        "race": getattr(char, "race", None) or "",
        "status": getattr(char, "status", "active"),
        "personality": getattr(char, "personality", ""),
        "disposition": getattr(char, "disposition", "neutral"),
    }


def _validate(
    result: CharacterActionSchema,
    scene: Scene | None = None,
    scene_objects: list[SceneObject] | None = None,
    pcs: dict[str, PlayerCharacter] | None = None,
    actors: dict[str, Actor] | None = None,
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
        elif not _target_in_scene(result.target_id, result.target_type, scene_objects, pcs, actors):
            logger.warning(
                "[engine] target %s (%s) not in scene, downgrading to wait",
                result.target_id,
                result.target_type,
            )
            result.action_type = "wait"
            result.target_id = None
            result.target_type = None

    # explore 时保留坐标，其他动作清空 / keep coords for explore, clear for others
    if result.action_type != "explore":
        result.explore_x = None
        result.explore_y = None

    if not result.thought or not result.thought.strip():
        result.thought = "我做出了这个决定。"
    return result


def _target_in_scene(
    target_id: str,
    target_type: str,
    scene_objects: list[SceneObject] | None = None,
    pcs: dict[str, PlayerCharacter] | None = None,
    actors: dict[str, Actor] | None = None,
) -> bool:
    """检查目标是否在当前场景 / Check if target exists in current scene."""
    if target_type == "scene_object":
        return any(o.id == target_id for o in (scene_objects or []))
    if target_type == "pc":
        return target_id in (pcs or {})
    if target_type == "actor":
        return target_id in (actors or {})
    return False
