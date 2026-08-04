"""Action 领域模型 / Action Domain Model.

待执行动作：一个 PC 决策执行后产出的结果封装。
"""

from .base import DomainModel


class Action(DomainModel):
    """角色动作执行结果."""

    order: int = 0
    pc_id: str = ""
    action_type: str = ""  # talk / interact / combat / explore
    target_id: str = ""
    target_type: str = ""

    # 各类动作公共字段 / common fields
    waypoints: list[dict] = []
    narration: str = ""

    # talk 相关 / talk-specific
    participants: list[str] = []
    turns: list[dict] = []

    # explore 相关 / explore-specific
    explore_record: str = ""

    # interact 相关 / interact-specific
    object_id: str = ""
    success: bool = False

    # combat 相关 / combat-specific
    winner: str | None = None
    target_defeated: bool = False
    result: str = ""
