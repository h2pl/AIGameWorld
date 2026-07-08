"""对话动作结果领域模型 / Talk action result domain model."""

from pydantic import BaseModel, Field


class TalkActionResult(BaseModel):
    """对话动作结果."""

    kind: str = "pc_talk"
    participants: list[str] = Field(default_factory=list)
    turns: list[dict] = Field(default_factory=list)
    waypoints: list[dict] = Field(default_factory=list)
