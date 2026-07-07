"""Action 领域模型 / Action Domain Model.

待执行动作：一个 PC 决策执行后产出的结果封装。
"""

from typing import Any

from .base import DomainModel


class Action(DomainModel):
    """角色动作执行结果."""

    order: int = 0
    pc_id: str = ""
    action_type: str = ""  # talk / interact / combat / explore
    target_id: str = ""
    target_type: str = ""
    result: Any = None
