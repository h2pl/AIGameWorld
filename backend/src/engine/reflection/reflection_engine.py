"""Reflection Engine——LLM 驱动的角色反思 / LLM-driven character reflection.

PC: 深度反思（弧线分析 + 性格洞察 + 下一步方向）
Actor: 浅层反思（行为模式总结）
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.runnables.config import RunnableConfig

from ...schemas.llm_output import ReflectionOutputSchema
from ...schemas.request import ReflectionRequest
from ...schemas.response import ReflectionResponse
from ...utils.helpers import get_llm
from ...utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts" / "reflection"
_PROMPTS = Environment(loader=FileSystemLoader(str(_PROMPTS_ROOT)))
_PC_TEMPLATE = _PROMPTS.get_template("reflect_pc.jinja")
_ACTOR_TEMPLATE = _PROMPTS.get_template("reflect_actor.jinja")


async def reflect(req: ReflectionRequest, config: RunnableConfig = None) -> ReflectionResponse:
    """角色反思入口 / Character reflection entry point."""
    llm = get_llm(config)
    if llm is None:
        logger.warning("[reflection] LLM not configured, returning empty insight for %s", req.pc_id)
        return ReflectionResponse(
            insights_out=[_format_insight(req, ReflectionOutputSchema().model_dump())]
        )

    template = _PC_TEMPLATE if req.pc_type == "pc" else _ACTOR_TEMPLATE
    prompt = template.render(
        pc_name=req.pc_name,
        arc_stage=req.arc_stage,
        arc_description=req.arc_description,
        memories=req.memories[-5:] if req.pc_type == "pc" else req.memories[-3:],
        recent_reflections=req.recent_reflections[-3:],
    )

    result = await llm.call_structured(
        f"reflect_{req.pc_type}",
        ReflectionOutputSchema,
        [{"role": "user", "content": prompt}],
    )
    insight = _format_insight(req, result.model_dump())
    return ReflectionResponse(insights_out=[insight])


def _format_insight(req: ReflectionRequest, result: dict) -> dict:
    """格式化反思输出 / Format reflection output."""
    if req.pc_type == "pc":
        text = " ".join(
            filter(None, [result.get("arc_analysis"), result.get("personality_insight")])
        )
        text = f"{req.pc_name}: {text or '（无有效反思）'}"
        importance = 10
    else:
        text = f"{req.pc_name}: {result.get('behavior_summary', '（无有效总结）')}"
        importance = 5

    return {
        "pc_id": req.pc_id,
        "insight": text,
        "memory_type": "reflection",
        "importance": importance,
        "tick": req.tick,
    }
