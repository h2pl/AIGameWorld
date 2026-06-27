"""Event Pydantic model.

Based on docs/06-data-layer.md §5.3.
"""

from pydantic import BaseModel, Field


class Event(BaseModel):
    """An event in the world – appended to the event log, never modified."""

    id: str  # evt_{tick}_{seq}
    tick: int
    seq: int = 0
    type: str  # combat_hit / character_talk / scene_change / plot / character_move / ...
    importance: int = 1  # 1=normal 2=important 3=critical
    source: str = "system"  # character id or "system"
    target: str | None = None
    data: dict = Field(default_factory=dict)
    narrative: str | None = None  # optional DM-generated narrative snippet
