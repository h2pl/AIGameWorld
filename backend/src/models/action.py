"""Action Pydantic model.

Based on docs/06-data-layer.md §5.3.
"""

from pydantic import BaseModel, Field


class Action(BaseModel):
    """Character agent output – handed to rule engines for resolution."""

    character_id: str  # PC or Actor id
    character_type: str = "pc"  # "pc" | "actor"
    tick: int = 0
    action_type: str = "wait"  # move / talk / attack / trade / interact / wait
    target: str | None = None
    reasoning: str = ""
    params: dict = Field(default_factory=dict)
