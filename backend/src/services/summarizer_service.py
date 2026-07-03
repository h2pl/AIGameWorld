"""Summarizer Service——LLM 驱动的事件压缩 / LLM-driven event summarization.

只是渲染 prompt + 调 LLM，不需要单独的 engine 层 /
Just rendering a prompt and calling the LLM — no separate engine layer is needed.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.runnables.config import RunnableConfig

from ..utils.helpers import get_llm
from ..utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent / "prompts" / "reflection"
_PROMPTS = Environment(loader=FileSystemLoader(str(_PROMPTS_ROOT)))
_TEMPLATE = _PROMPTS.get_template("summarize.jinja")


async def summarize(state: dict, config: RunnableConfig = None) -> dict:
    """压缩 tick_events → summary_text，供 reflection 阶段消费 / Compress tick_events into summary_text."""
    events = state.get("tick_events", state.get("events", []))
    character_count = state.get("character_count", 0)

    llm = get_llm(config)
    if llm is None or not events:
        return {"summary_compressed": False, "tick_events": events}

    prompt = _TEMPLATE.render(events=events, event_count=len(events), char_count=character_count)
    try:
        result = await llm.call_structured(
            "summarize", None, [{"role": "user", "content": prompt}], fallback=dict
        )
        summary = result.get("summary", "")
        return {
            "summary_compressed": bool(summary),
            "summary_text": summary,
            "tick_events": events,
        }
    except Exception:
        logger.exception("[summarizer] summarize failed")
        return {"summary_compressed": False, "tick_events": events}
