"""Summarizer Service: State ↔ Engine adapter."""
from typing import Any
from ..models.io.reflection import SummarizerInput
from ..engine.summarizer.summarizer import summarize as _summarize
from ..graph.state import ReflectionSubState


def summarize(state: ReflectionSubState) -> dict[str, Any]:
    """Phase 7: 事件压缩."""
    _summarize(SummarizerInput(
        events=state.get("events", []),
        tick=state.get("tick", 0),
    ))
    return {"summary_compressed": False}
