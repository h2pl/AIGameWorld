"""Summarizer Engine: 纯业务逻辑."""

from ...schemas.request import SummarizerRequest
from ...schemas.response import SummarizerResponse


def summarize(req: SummarizerRequest) -> SummarizerResponse:
    """压缩事件. Mock. Phase 3 接入 LLM."""
    return SummarizerResponse(
        compressed=len(req.events) > 3,
        summary_text=f"Mock: {len(req.events)} events at tick {req.tick}.",
    )
