"""Summarizer Service——事件压缩 / Event summarization."""

import logging

from langchain_core.runnables.config import RunnableConfig

from ..engine.summarizer import summarizer as summarizer_engine
from ..graph.state import ReflectionSubState
from ..schemas.request import SummarizerRequest

logger = logging.getLogger(__name__)


async def summarize(state: ReflectionSubState, config: RunnableConfig = None) -> dict:
    """Phase 7: 压缩本轮事件 / Compress this tick's events."""
    events = state.get("events", [])
    char_count = len(state.get("reflected_characters", []))

    result = await summarizer_engine.summarize(
        SummarizerRequest(
            events=events,
            character_count=max(char_count, 1),
            tick=state.get("tick", 0),
        ),
        config,
    )

    return {
        "summary_compressed": result.compressed,
        "events": result.summary_text if result.compressed else "",
    }
