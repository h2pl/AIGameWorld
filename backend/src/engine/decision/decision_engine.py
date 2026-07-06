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
# 合法动作集合 / Valid action types
_VALID_ACTIONS = {"talk", "interact", "combat", "explore", "wait"}
# 动作与合法目标类型映射 / Action → allowed target types
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
    config: RunnableConfig = None,
) -> list[dict]:
    """基于场景信息为单个 PC 决策，返回 1~3 个动作列表 / Decide for a PC, return 1-3 actions."""
    logger.info("[engine] decide tick=%s pc=%s", tick, pc_id or "-")

    llm = get_llm(config)
    if llm is None:
        return [_fallback_decision(pc_id)]

    try:
        pcs = scene_info.get("pcs", [])
        # 当前 PC 自身信息 / Current PC info
        me = next((pc for pc in pcs if pc.get("id") == pc_id), None) or {
            "id": pc_id,
            "name": pc_id,
            "role": "",
            "race": "",
            "status": "active",
        }
        # 同场景其他 PC / Other PCs in the same scene
        nearby_pcs = [pc for pc in pcs if pc.get("id") != pc_id]
        # 检索相关记忆 / Retrieve relevant memories
        query = f"{plot_brief} {scene_info.get('scene', {}).get('description', '')}".strip()
        memories = await retrieve_memories(pc_id, query, config=config, top_k=5)

        # 渲染 prompt 所需的上下文 / Context for prompt rendering
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
            "nearby_actors": scene_info.get("actors", []),
        }
        system = _PROMPTS.get_template("decide/_pc_system.jinja").render(**ctx)
        try:
            prompt = _PROMPTS.get_template("decide/pc_decide.jinja").render(**ctx)
        except Exception:
            prompt = f"Plot brief: {plot_brief}\nOutput a JSON array of 1-3 actions."

        result = await llm.call_structured(
            "pc_decision",
            PCDecideListSchema,
            [SystemMessage(content=system), HumanMessage(content=prompt)],
            fallback=lambda: PCDecideListSchema(
                actions=[CharacterActionSchema(action_type="wait", reasoning="LLM 降级。")]
            ),
        )

        decisions: list[dict] = []
        for action in result.actions:
            validated = _validate(action, scene_info)
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

    except Exception:
        logger.exception("[engine] failed for pc %s", pc_id)
        return [_fallback_decision(pc_id)]


def _fallback_decision(pc_id: str) -> dict:
    return PCDecideResponse(
        pc_id=pc_id,
        type="wait",
        description="等待时机。",
    ).model_dump()


def _validate(
    result: CharacterActionSchema, scene_info: dict | None = None
) -> CharacterActionSchema:
    """校验并修正 LLM 返回的动作 / Validate LLM action, fallback to wait for invalid combos."""
    # 未知动作 / Unknown action
    if result.action_type not in _VALID_ACTIONS:
        result.action_type = "wait"
    # wait/explore 不需要目标 / No target needed
    if result.action_type in ("wait", "explore"):
        result.target_id = None
        result.target_type = None
    else:
        # 格式校验 / Format check
        allowed_types = _ACTION_TARGET_TYPES.get(result.action_type, set())
        if not result.target_id or result.target_type not in allowed_types:
            result.action_type = "wait"
            result.target_id = None
            result.target_type = None
        # 存在性校验：目标必须在当前场景中 / Existence check: target must be in current scene
        elif scene_info and not _target_in_scene(result.target_id, result.target_type, scene_info):
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


def _target_in_scene(target_id: str, target_type: str, scene_info: dict) -> bool:
    """检查目标是否在当前场景 / Check if target exists in current scene"""
    if target_type == "scene_object":
        objects = scene_info.get("scene_objects", [])
        return any(o.get("id") == target_id for o in objects)
    # pc / actor
    key = "pcs" if target_type == "pc" else "actors"
    chars = scene_info.get(key, [])
    return any(c.get("id") == target_id for c in chars)
