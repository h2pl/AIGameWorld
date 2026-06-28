"""Summarizer Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class SummarizerSubState(TypedDict):
    """Summarizer Service 内部数据契约 / Summarizer service internal data contract."""
    events: list[dict[str, Any]]
    tick: int
    summary: str


def summarize(events: list[dict[str, Any]], tick: int) -> str:
    """压缩事件 / Compress events. Mock."""
    return ""
