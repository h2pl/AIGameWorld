"""PC 决策领域模型 / PC Decision domain model.

每个 PC 每 tick 只产生一条决策，供 pc_service.act 分发给各 engine。
"""

from pydantic import BaseModel, ConfigDict


class Decision(BaseModel):
    """PC 决策——一次行动选择."""

    model_config = ConfigDict(extra="forbid")

    pc_id: str
    type: str = ""  # talk / interact / combat / explore / wait
    target_id: str | None = None
    target_type: str | None = None
    thought: str = ""  # 完整思考 / full reasoning
    description: str = ""  # 最终决策理由 / final rationale
    explore_x: int | None = None
    explore_y: int | None = None

    @property
    def action_type(self) -> str:
        """与 action 事件对齐的别名 / Alias aligned with action events."""
        return self.type
