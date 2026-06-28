"""事件领域模型 / Event Domain Model."""
from __future__ import annotations
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ...schemas.response import WorldUpdateResponse


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

    @classmethod
    def from_world_response(cls, resp: WorldUpdateResponse, tick: int) -> list[Event]:
        """Schema Response → Domain Models"""
        import uuid
        return [
            cls(
                id=f"evt_{tick}_{i}",
                tick=tick,
                seq=i,
                type=evt.get("type", "world"),
                data=evt,
            )
            for i, evt in enumerate(resp.events_out)
        ]
