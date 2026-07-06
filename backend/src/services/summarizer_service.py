"""Summarizer Service——LLM 驱动的 tick 总结 / LLM-driven tick summary.

仅负责反射阶段的 tick_events 压缩总结，不负责 DM 叙事。
DM 叙事已由 dm_service.dm_narrate 接管。
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.runnables.config import RunnableConfig

from ..schemas.llm_output import SummaryOutputSchema
from ..utils.helpers import get_llm
from ..utils.logging import get_logger, trace_node

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(str(_PROMPTS_ROOT)))


@trace_node("summarizer.summarize")
async def summarize(state: dict, config: RunnableConfig = None) -> dict:
    """压缩 tick_events → summary_text（反射阶段使用）/ Compress events for reflection."""
    events = state.get("tick_events", state.get("events", []))
    character_count = state.get("character_count", 0)

    if not events:
        return {"summary_compressed": False, "tick_events": events}

    llm = get_llm(config)
    if llm is None:
        logger.warning("[summarizer] LLM not configured, skipping compression")
        return {"summary_compressed": False, "tick_events": events}

    prompt = _PROMPTS.get_template("reflection/summarize.jinja").render(
        events=events, event_count=len(events), char_count=character_count
    )
    result = await llm.call_structured(
        "summarize",
        SummaryOutputSchema,
        [{"role": "user", "content": prompt}],
    )
    summary = result.summary
    return {
        "summary_compressed": bool(summary),
        "summary_text": summary,
        "tick_events": events,
    }
