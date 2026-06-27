"""DM 指令模型 / DM Instruction Models.

基于 design/06-data-layer.md §5.3, 架构方案 §6.7.
DM Phase 1 产出 4 种指令，驱动 WorldEngine 执行.
"""

from typing import Literal

from pydantic import BaseModel, Field


class DMInstruction(BaseModel):
    """DM 生成的驱动指令基类 / Base class for DM-generated instructions."""

    type: Literal["plot_event", "actor_motivation", "scene_change", "scene_direction"]
    priority: int = 0          # 优先级 / Priority
    description: str = ""      # 描述 / Description


class PlotEvent(DMInstruction):
    """情节事件: 怪物袭击/势力冲突/任务发放/发现 / Plot event."""

    type: Literal["plot_event"] = "plot_event"  # type discriminator
    event_subtype: Literal["actor_arrival", "monster_attack", "faction_conflict",
                           "quest_issue", "discovery"] = "discovery"
    spawn_actors: list[dict] = Field(default_factory=list)  # 生成的 Actor 列表
    spawn_scene: str | None = None
    affect_scene: str | None = None
    event_data: dict = Field(default_factory=dict)


class ActorMotivation(DMInstruction):
    """Actor 动机注入: 目标/性格/情绪 / Actor motivation injection."""

    type: Literal["actor_motivation"] = "actor_motivation"
    target_actor_id: str = ""       # 目标 Actor ID / Target actor
    new_goal: str | None = None     # 新目标 / New goal
    personality_shift: dict | None = None  # 性格转变 / Personality shift
    emotional_state: str | None = None     # 情绪状态 / Emotional state


class SceneChange(DMInstruction):
    """场景变化: 天气/时段/环境事件 / Scene change."""

    type: Literal["scene_change"] = "scene_change"
    scene_id: str = ""                      # 目标场景 / Target scene
    weather: str | None = None              # 天气 / Weather
    time_of_day: str | None = None          # 时段 / Time of day
    environmental_event: str | None = None  # 环境事件 / Environmental event


class SceneDirection(DMInstruction):
    """DM 导演指令: 指定本步参演人员 / Scene direction (cast selection)."""

    type: Literal["scene_direction"] = "scene_direction"
    featured_pcs: list[str] = Field(default_factory=list)      # 重点主角团 / Featured PCs
    featured_actors: list[str] = Field(default_factory=list)    # 出场 Actor / Featured actors
    actor_motivations: dict[str, str] = Field(default_factory=dict)  # Actor → motivation 映射
