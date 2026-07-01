"""故事摘要领域模型 / Story Summary Domain Model."""

from .base import DomainModel


class StorySummary(DomainModel):
    """故事摘要——每 N tick 异步压缩."""

    tick_start: int = 0
    tick_end: int = 0
    summary: str = ""
