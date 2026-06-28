"""角色行动领域模型."""
from pydantic import BaseModel, Field


class Action(BaseModel):
    """角色行动——Agent 输出 → 规则引擎输入."""

    character_id: str
    character_type: str = "pc"
    tick: int = 0
    action_type: str = "wait"
    target: str | None = None
    reasoning: str = ""
    params: dict = Field(default_factory=dict)
