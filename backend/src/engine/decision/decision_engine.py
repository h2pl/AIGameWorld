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
from ...utils.helpers import get_llm

logger = logging.getLogger("aw.eng.char")

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))
# combat 预留：战斗结算尚未接入 act 执行层 / combat reserved: not yet wired into the act phase
# TODO: 实现 combat 动作在 act 阶段的执行（调用 combat_engine）
_VALID_ACTIONS = {"talk", "interact", "combat", "wait"}
# action_type 对应允许的 target_type / Allowed target_type per action_type
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
) -> dict | None:
    """基于场景信息为单个 PC 决策（scene_info 与谁来用无关，不区分 PC，这里按
    pc_id 从中取出"me"和"其他 PC"）/
    Decide for a single PC based on the scene info (scene_info is
    consumer-independent, not per-PC; "me" and "other PCs" are derived here
    from pc_id)."""
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
        pcs = scene_info.get("pcs", [])
        me = next((pc for pc in pcs if pc.get("id") == pc_id), None) or {
            "id": pc_id,
            "name": pc_id,
            "role": "",
            "race": "",
            "status": "active",
        }
        nearby_pcs = [pc for pc in pcs if pc.get("id") != pc_id]
        ctx = {
            "me": me,
            "plot_brief": plot_brief,
            "hints": hints,
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
            prompt = f"Plot brief: {plot_brief}\nRespond with the next action."
        result = await llm.call_structured(
            "pc_decision",
            CharacterActionSchema,
            [SystemMessage(content=system), HumanMessage(content=prompt)],
            fallback=lambda: CharacterActionSchema(action_type="wait", reasoning="LLM 降级。"),
        )
        result = _validate(result)
        return PCDecideResponse(
            pc_id=pc_id,
            type=result.action_type,
            target_id=result.target_id,
            target_type=result.target_type,
            description=result.reasoning,
        ).model_dump()
    except Exception:
        logger.exception("[character] failed for pc %s", pc_id)
        return PCDecideResponse(
            pc_id=pc_id,
            type="wait",
            description="等待时机。",
            errors=["pc_decide LLM 调用失败，使用降级输出"],
        ).model_dump()


def _validate(result: CharacterActionSchema) -> CharacterActionSchema:
    if result.action_type not in _VALID_ACTIONS:
        result.action_type = "wait"

    if result.action_type == "wait":
        # wait 不需要 target，强制清空 / wait needs no target, force clear it
        result.target_id = None
        result.target_type = None
    else:
        # 非 wait 动作必须有合法且与 action_type 匹配的 target，否则降级为 wait
        # non-wait actions must have a valid target matching action_type, else fall back to wait
        allowed_types = _ACTION_TARGET_TYPES.get(result.action_type, set())
        if not result.target_id or result.target_type not in allowed_types:
            result.action_type = "wait"
            result.target_id = None
            result.target_type = None

    if not result.reasoning or not result.reasoning.strip():
        result.reasoning = "等待时机。"
    return result
