"""Summarizer Node: State <-> Service glue / 摘要节点：State ↔ Service 胶水。"""
from typing import Any
from ..engine.summarizer.summarizer import summarize


def summarizer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Phase 7: 事件压缩 / Event summarization.

    产出 / Outputs: summary
    """
    summary = summarize(
        events=state.get("events", []),
        tick=state.get("tick", 0),
    )
    return {"summary": summary}
