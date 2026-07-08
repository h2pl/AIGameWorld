"""Reflection Engine——LLM 驱动的角色反思 / LLM-driven character reflection.

PC: 深度反思（弧线分析 + 性格洞察 + 下一步方向）
Actor: 浅层反思（行为模式总结）
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.runnables.config import RunnableConfig

from ...domain import Memory
from ...schemas.llm_output import ReflectionOutputSchema
from ...utils.helpers import get_llm
from ...utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts" / "reflection"
_PROMPTS = Environment(loader=FileSystemLoader(str(_PROMPTS_ROOT)))
_PC_TEMPLATE = _PROMPTS.get_template("reflect_pc.jinja")
_ACTOR_TEMPLATE = _PROMPTS.get_template("reflect_actor.jinja")


async def reflect(
    pc_id: str,
    pc_name: str,
    pc_type: str,
    arc_stage: str,
    arc_description: str,
    memories: list[Memory],
    recent_reflections: list[str],
    tick: int = 0,
    config: RunnableConfig = None,
) -> list[dict]:
    """角色反思入口 / Character reflection entry point."""
    llm = get_llm(config)
    if llm is None:
        logger.warning("[reflection] LLM not configured, returning empty insight for %s", pc_id)
        return [
            _format_insight(
                pc_id,
                pc_name,
                pc_type,
                tick,
                {"arc_analysis": "", "personality_insight": "", "behavior_summary": ""},
            )
        ]

    template = _PC_TEMPLATE if pc_type == "pc" else _ACTOR_TEMPLATE
    prompt = template.render(
        pc_name=pc_name,
        arc_stage=arc_stage,
        arc_description=arc_description,
        memories=memories[-5:] if pc_type == "pc" else memories[-3:],
        recent_reflections=recent_reflections[-3:],
    )

    result = await llm.call_structured(
        f"reflect_{pc_type}",
        ReflectionOutputSchema,
        [{"role": "user", "content": prompt}],
    )
    return [_format_insight(pc_id, pc_name, pc_type, tick, result)]


def _format_insight(pc_id: str, pc_name: str, pc_type: str, tick: int, result) -> dict:
    """格式化反思输出 / Format reflection output."""
    if pc_type == "pc":
        text = " ".join(
            filter(
                None,
                [
                    getattr(result, "arc_analysis", None),
                    getattr(result, "personality_insight", None),
                ],
            )
        )
        text = f"{pc_name}: {text or '（无有效反思）'}"
        importance = 10
    else:
        text = f"{pc_name}: {getattr(result, 'behavior_summary', '（无有效总结）')}"
        importance = 5

    return {
        "pc_id": pc_id,
        "insight": text,
        "memory_type": "reflection",
        "importance": importance,
        "tick": tick,
    }
