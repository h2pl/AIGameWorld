"""行动 Pydantic 模型 / Action Pydantic model.

基于 docs/06-data-layer.md §5.3 / Based on docs/06-data-layer.md §5.3.

Action 是角色 Agent（PC/Actor）的输出，交给规则引擎裁决。
Action is the output of character agents (PC/Actor), handed to rule engines for resolution.
"""

from pydantic import BaseModel, Field


class Action(BaseModel):
    """角色行动——Agent 输出 → 规则引擎输入 / Character action — Agent output → Rule engine input."""

    character_id: str               # PC 或 Actor 的 ID / PC or Actor ID
    character_type: str = "pc"      # 角色类型: "pc" | "actor"
    tick: int = 0                   # 发生的 tick
    action_type: str = "wait"       # 行动类型: move/talk/attack/trade/interact/wait
    target: str | None = None       # 目标对象 / Target
    reasoning: str = ""             # 决策推理（可追溯到角色弧和记忆）/ Reasoning (traceable to arc & memory)
    params: dict = Field(default_factory=dict)  # 附加参数 / Additional params
