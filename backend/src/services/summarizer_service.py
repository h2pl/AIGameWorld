"""Summarizer Service: State ↔ Engine adapter."""

from ..engine.summarizer import summarizer as summarizer_engine
from ..graph.state import ReflectionSubState
from ..schemas.request import SummarizerRequest


def summarize(state: ReflectionSubState) -> dict:
    """Phase 7: 事件压缩."""
    result = summarizer_engine.summarize(
        SummarizerRequest(
            events=state.get("events", []),
            tick=state.get("tick", 0),
        )
    )
    return {"summary_compressed": result.compressed}
