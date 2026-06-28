"""Summarizer Service: State ↔ Engine adapter / 摘要服务：State ↔ Engine 适配。"""
from typing import Any
from ..engine.summarizer.summarizer import SummarizerInput, summarize as _summarize
from ..graph.state import ReflectionSubState


def _to_summarize_input(state: ReflectionSubState) -> SummarizerInput:
    """① State → Engine 输入"""
    return {
        "events": state.get("events", []),
        "tick": state.get("tick", 0),
    }


def summarize(state: ReflectionSubState) -> dict[str, Any]:
    """Phase 7: 事件压缩 / Event summarization.

    ① State → SummarizerInput
    ② 调用 Engine
    ③ 映射回 State key
    产出 / Outputs: summary_compressed
    """
    engine_input = _to_summarize_input(state)   # ①
    _summarize(engine_input)                    # ②
    return {"summary_compressed": False}         # ③
