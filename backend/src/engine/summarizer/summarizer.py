"""Summarizer Engine——LLM 驱动的事件压缩 / LLM-driven event summarization."""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.runnables.config import RunnableConfig

from ...schemas.request import SummarizerRequest
from ...schemas.response import SummarizerResponse
from ...utils.helpers import get_llm

logger = logging.getLogger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts" / "reflection"
_PROMPTS = Environment(loader=FileSystemLoader(str(_PROMPTS_ROOT)))
_TEMPLATE = _PROMPTS.get_template("summarize.jinja")


async def summarize(req: SummarizerRequest, config: RunnableConfig = None) -> SummarizerResponse:
    """压缩事件 / Compress events."""
    llm = get_llm(config)
    if llm is None:
        return SummarizerResponse(
            compressed=False,
            summary_text="",
            errors=["LLM 不可用，使用降级输出 / LLM unavailable, fallback"],
        )

    if not req.events:
        return SummarizerResponse(compressed=False, summary_text="无事件可压缩。")

    prompt = _TEMPLATE.render(
        events=req.events,
        event_count=len(req.events),
        char_count=req.character_count,
    )

    try:
        result = await llm.call_structured(
            "summarize",
            None,
            [{"role": "user", "content": prompt}],
            fallback=dict,
        )
        summary = result.get("summary", "")
        return SummarizerResponse(compressed=bool(summary), summary_text=summary)
    except Exception:
        logger.exception("summarize failed")
        return SummarizerResponse(
            compressed=False,
            summary_text="",
            errors=["LLM 调用失败，使用降级输出 / LLM call failed, fallback"],
        )
