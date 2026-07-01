"""消息 / Message — 一次 tick 产出的完整数据包."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .event import Event


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    tick: int
    world_id: str
    timestamp: datetime
    events: list[Event] = Field(default_factory=list)
