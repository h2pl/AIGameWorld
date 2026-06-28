"""Summarizer Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from ...models.io.reflection import SummarizerInput


def summarize(input: SummarizerInput) -> str:
    """压缩事件 / Compress events. Mock."""
    return ""
