"""Engine Action 返回结果模型 / Engine action result schemas.

talk / interact / explore 三个 engine 的 process_*_action 返回值统一使用这些模型。
waypoints 使用 `list[dict]`，与 internal 方法原生格式一致，不额外转换。
"""

from pydantic import BaseModel, Field


class ExploreActionResult(BaseModel):
    """探索动作结果."""

    kind: str = "pc_explore"
    pc_id: str
    waypoints: list[dict] = Field(default_factory=list)
    explore_record: str = ""


class InteractActionResult(BaseModel):
    """交互动作结果."""

    kind: str = "pc_interact"
    pc_id: str
    object_id: str = ""
    success: bool = False
    waypoints: list[dict] = Field(default_factory=list)
    narration: str = ""


class TalkActionResult(BaseModel):
    """对话动作结果."""

    kind: str = "pc_talk"
    participants: list[str] = Field(default_factory=list)
    turns: list[dict] = Field(default_factory=list)
    waypoints: list[dict] = Field(default_factory=list)


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
