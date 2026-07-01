"""故事摘要领域模型 / Story Summary Domain Model."""

from pydantic import BaseModel


class StorySummary(BaseModel):
    """故事摘要——每 N tick 异步压缩."""

    world_id: str = ""
    tick_start: int = 0
    tick_end: int = 0
    summary: str = ""
