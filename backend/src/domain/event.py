"""事件领域模型."""
from pydantic import BaseModel, Field


class Event(BaseModel):
    """世界事件——追加写到 event_log，永不修改."""

    id: str
    tick: int
    seq: int = 0
    type: str
    importance: int = 1
    source: str = "system"
    target: str | None = None
    data: dict = Field(default_factory=dict)
    narrative: str | None = None
