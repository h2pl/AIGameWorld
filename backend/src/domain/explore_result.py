"""探索动作结果领域模型 / Explore action result domain model."""

from pydantic import BaseModel, Field


class ExploreActionResult(BaseModel):
    """探索动作结果."""

    kind: str = "pc_explore"
    pc_id: str
    waypoints: list[dict] = Field(default_factory=list)
    explore_record: str = ""
