"""消息 / Message — 一次 tick 产出的完整数据包."""

from datetime import datetime

from .base import DomainModel


class TickMessage(DomainModel):
    id: str
    tick: int
    tick_events: list[dict] = []
    timestamp: datetime | None = None


Message = TickMessage
