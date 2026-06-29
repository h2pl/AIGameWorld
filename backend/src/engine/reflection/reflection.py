"""Reflection Engine——LLM 驱动的角色反思 / LLM-driven character reflection.

PC: 深度反思（弧线分析 + 性格洞察 + 下一步方向）
Actor: 浅层反思（行为模式总结）
"""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.runnables.config import RunnableConfig

from ...schemas.request import ReflectionRequest
from ...schemas.response import ReflectionResponse
from ...utils.helpers import get_llm

logger = logging.getLogger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts" / "reflection"
_PROMPTS = Environment(loader=FileSystemLoader(str(_PROMPTS_ROOT)))
_PC_TEMPLATE = _PROMPTS.get_template("reflect_pc.jinja")
_ACTOR_TEMPLATE = _PROMPTS.get_template("reflect_actor.jinja")


async def reflect(req: ReflectionRequest, config: RunnableConfig = None) -> ReflectionResponse:
    """角色反思入口 / Character reflection entry point."""
    llm = get_llm(config)
    if llm is None:
        return _fallback(req, ["LLM 不可用，使用降级输出 / LLM unavailable, fallback used"])

    template = _PC_TEMPLATE if req.character_type == "pc" else _ACTOR_TEMPLATE
    prompt = template.render(
        character_name=req.character_name,
        arc_stage=req.arc_stage,
        arc_description=req.arc_description,
        memories=req.memories[-5:] if req.character_type == "pc" else req.memories[-3:],
        recent_reflections=req.recent_reflections[-3:],
    )

    try:
        result = await llm.call_structured(
            f"reflect_{req.character_type}",
            None,
            [{"role": "user", "content": prompt}],
            fallback=dict,
        )
        insight = _format_insight(req, result)
        return ReflectionResponse(insights_out=[insight])
    except Exception:
        logger.exception("reflect failed for %s (%s)", req.character_id, req.character_type)
        return _fallback(req, ["LLM 调用失败，使用降级输出 / LLM call failed, fallback used"])


def _format_insight(req: ReflectionRequest, result: dict) -> dict:
    """格式化反思输出 / Format reflection output."""
    if req.character_type == "pc":
        text = " ".join(
            filter(None, [result.get("arc_analysis"), result.get("personality_insight")])
        )
        text = f"{req.character_name}: {text or '（无有效反思）'}"
        importance = 10
    else:
        text = f"{req.character_name}: {result.get('behavior_summary', '（无有效总结）')}"
        importance = 5

    return {
        "character_id": req.character_id,
        "insight": text,
        "memory_type": "reflection",
        "importance": importance,
        "tick": req.tick,
    }


def _fallback(req: ReflectionRequest, errors: list[str] | None = None) -> ReflectionResponse:
    """降级输出 / Fallback output."""
    return ReflectionResponse(
        insights_out=[{
            "character_id": req.character_id,
            "insight": f"{req.character_name}: 维持当前行为模式。",
            "memory_type": "reflection",
            "importance": 0,
            "tick": req.tick,
        }],
        errors=errors or ["LLM 不可用，使用降级输出"],
    )
