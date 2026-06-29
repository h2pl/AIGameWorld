"""PC Decide Engine——LLM 驱动的深层决策 / PC deep decision with LLM."""

# ── 依赖 / Dependencies ──
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ...schemas.llm_output import CharacterActionSchema
from ...schemas.request import PCDecideRequest
from ...schemas.response import PCDecideResponse
from ...utils.helpers import get_llm, get_repo

logger = logging.getLogger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))
_VALID_ACTIONS = {"move", "talk", "attack", "interact", "wait"}

# ── 主决策入口 / Main decision entry ──


async def pc_decide(req: PCDecideRequest, config: RunnableConfig = None) -> PCDecideResponse:
    llm = get_llm(config)
    if llm is None:
        return PCDecideResponse(character_id=req.pc_id, type="wait", description="等待时机。", errors=["LLM 不可用，使用降级输出 / LLM unavailable, fallback used"])
    try:
        char_repo = get_repo(config, "char")
        memory_repo = get_repo(config, "memory")
        pc = await char_repo.load_pc(req.pc_id) if char_repo else None
        query = req.plot_brief or "最近发生了什么"
        memories = memory_repo.retrieve(req.pc_id, query, top_k=5) if memory_repo else []
        ctx = {
            "name": pc.name if pc else req.pc_id,
            "character_type": "pc",
            "role": pc.role if pc else "",
            "character_arc": pc.character_arc.model_dump() if pc and pc.character_arc else {},
            "values": pc.values if pc else [],
            "long_term_goal": pc.long_term_goal if pc else "",
            "plot_brief": req.plot_brief,
            "equipment": pc.equipment.model_dump() if pc and pc.equipment else {},
            "memories": [{"content": m.content} for m in memories],
        }
        system = _PROMPTS.get_template("_character_system.jinja").render(**ctx)
        prompt = _PROMPTS.get_template("character/pc_decide.jinja").render(**ctx)
        result = await llm.call_structured(
            "pc_decision",
            CharacterActionSchema,
            [SystemMessage(content=system), HumanMessage(content=prompt)],
            fallback=lambda: CharacterActionSchema(action_type="wait", reasoning="LLM 降级。"),
        )
        result = _validate(result)
        return PCDecideResponse(
            character_id=req.pc_id, type=result.action_type, description=result.reasoning
        )
    except Exception:
        logger.exception("pc_decide LLM failed for %s", req.pc_id)
        return PCDecideResponse(character_id=req.pc_id, type="wait", description="等待时机。", errors=["pc_decide LLM 调用失败，使用降级输出"])


def _validate(result: CharacterActionSchema) -> CharacterActionSchema:
    if result.action_type not in _VALID_ACTIONS:
        result.action_type = "wait"
    if not result.reasoning or not result.reasoning.strip():
        result.reasoning = "等待时机。"
    return result

