"""故事领域模型 / Story Domain Models."""

from pydantic import BaseModel, Field


class Quest(BaseModel):
    """任务——DM 生成，主角团尝试完成."""

    id: str
    arc_id: str | None = None
    title: str = ""
    description: str = ""
    status: str = "inactive"
    progress: dict = Field(default_factory=dict)
    assigned_pcs: list[str] = Field(default_factory=list)
    created_tick: int | None = None
    completed_tick: int | None = None
