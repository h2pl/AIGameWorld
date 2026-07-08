"""交互动作结果领域模型 / Interact action result domain model."""

from pydantic import BaseModel, Field


class InteractActionResult(BaseModel):
    """交互动作结果."""

    kind: str = "pc_interact"
    pc_id: str
    object_id: str = ""
    success: bool = False
    waypoints: list[dict] = Field(default_factory=list)
    narration: str = ""
