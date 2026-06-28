"""Summarizer Engine: 纯业务逻辑."""

from ...schemas.request import SummarizerRequest


def summarize(req: SummarizerRequest) -> str:
    """压缩事件. Mock."""
    return ""
