"""Summarizer Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from typing import TypedDict, Any


class SummarizerInput(TypedDict):
    """Phase 7: 事件压缩的 Engine 输入"""
    events: list[dict[str, Any]]
    tick: int


def summarize(input: SummarizerInput) -> str:
    """压缩事件 / Compress events. Mock."""
    return ""
