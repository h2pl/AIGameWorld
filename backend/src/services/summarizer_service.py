"""Summarizer Service: State ↔ Engine adapter."""
from typing import Any
from ..models.reflection import SummarizerInput
from ..engine.summarizer.summarizer import summarize as _summarize
from ..graph.state import ReflectionSubState


def _to_summarize_input(state: ReflectionSubState) -> SummarizerInput:
    return {"events": state.get("events", []), "tick": state.get("tick", 0)}


def summarize(state: ReflectionSubState) -> dict[str, Any]:
    """Phase 7: 事件压缩. 产出 / Outputs: summary_compressed"""
    _summarize(_to_summarize_input(state))
    return {"summary_compressed": False}
