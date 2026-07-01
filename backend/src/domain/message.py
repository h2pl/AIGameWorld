"""消息 / Message — 一次 tick 产出的完整数据包."""

from datetime import datetime

from .base import DomainModel


class Message(DomainModel):
    id: str
    tick: int
    timestamp: datetime | None = None
