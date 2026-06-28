"""DM 指令模型 / DM Instruction Models.

基于 design/06-data-layer.md §5.3, 架构方案 §6.7.
DM Phase 1 产出 4 种指令，驱动 WorldEngine 执行.
"""

from __future__ import annotations
from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .io.dm import DMCreateInput, DMCreateOutput


class DMInstruction(BaseModel):
    """DM 生成的驱动指令基类 / Base class for DM-generated instructions."""

    type: Literal["plot_event", "actor_motivation", "scene_change", "scene_direction"]
    priority: int = 0
    description: str = ""

    @classmethod
    def from_input(cls, input: DMCreateInput) -> DMInstruction:
        """Engine Input → Domain Model"""
        return cls(tick=input.tick, plot_brief=input.plot_brief, type="scene_direction")

    def to_output(self, output: DMCreateOutput | None = None) -> DMCreateOutput:
        """Domain Model → Engine Output"""
        from .dm import DMCreateOutput
        return DMCreateOutput(
            instructions_out=[self.model_dump()],
            plot_brief=getattr(self, "plot_brief", ""),
            scene_direction=getattr(self, "scene_direction", {}),
        )


class PlotEvent(DMInstruction):
    """情节事件: 怪物袭击/势力冲突/任务发放/发现 / Plot event."""

    type: Literal["plot_event"] = "plot_event"
    event_subtype: Literal["actor_arrival", "monster_attack", "faction_conflict",
                           "quest_issue", "discovery"] = "discovery"
    spawn_actors: list[dict] = Field(default_factory=list)
    spawn_scene: str | None = None
    affect_scene: str | None = None
    event_data: dict = Field(default_factory=dict)


class ActorMotivation(DMInstruction):
    """Actor 动机注入: 目标/性格/情绪 / Actor motivation injection."""

    type: Literal["actor_motivation"] = "actor_motivation"
    target_actor_id: str = ""
    new_goal: str | None = None
    personality_shift: dict | None = None
    emotional_state: str | None = None


class SceneChange(DMInstruction):
    """场景变化: 天气/时段/环境事件 / Scene change."""

    type: Literal["scene_change"] = "scene_change"
    scene_id: str = ""
    weather: str | None = None
    time_of_day: str | None = None
    environmental_event: str | None = None


class SceneDirection(DMInstruction):
    """DM 导演指令: 指定本步参演人员 / Scene direction (cast selection)."""

    type: Literal["scene_direction"] = "scene_direction"
    featured_pcs: list[str] = Field(default_factory=list)
    featured_actors: list[str] = Field(default_factory=list)
    actor_motivations: dict[str, str] = Field(default_factory=dict)
