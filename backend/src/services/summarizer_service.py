"""Summarizer Service: State ↔ Engine adapter / 摘要服务：State ↔ Engine 适配。"""
from typing import Any
from ..engine.summarizer.summarizer import summarize as _summarize
from ..graph.state import ReflectionSubState


def summarize(state: ReflectionSubState) -> dict[str, Any]:
    """Phase 7: 事件压缩 / Event summarization.

    产出 / Outputs: summary_compressed
    """
    _summarize(
        events=state.get("events", []),
        tick=state.get("tick", 0),
    )
    return {"summary_compressed": False}
