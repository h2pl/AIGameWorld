"""战斗动作结果领域模型 / Combat action result domain model."""

from pydantic import BaseModel, Field


class CombatActionResult(BaseModel):
    """战斗动作结果."""

    kind: str = "pc_combat"
    pc_id: str
    target_id: str = ""
    target_type: str = ""
    waypoints: list[dict] = Field(default_factory=list)
    narration: str = ""
    combat_log: list[dict] = Field(default_factory=list)
    winner: str | None = None
    target_defeated: bool = False
    result: str = ""
