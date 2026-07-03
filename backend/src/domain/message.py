"""消息 / Message — 一次 tick 产出的完整数据包."""

from .base import DomainModel


class TickMessage(DomainModel):
    id: str
    tick: int
    status: str = "building"  # building | pending | consumed
    is_last: bool = False


Message = TickMessage
