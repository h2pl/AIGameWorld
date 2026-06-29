"""DM 指令领域模型."""

from typing import Literal

from pydantic import BaseModel, Field


class DMInstruction(BaseModel):
    """DM 生成的驱动指令基类."""

    type: Literal["plot_event", "actor_motivation", "scene_change", "scene_direction"]
    priority: int = 0
    description: str = ""


class PlotEvent(DMInstruction):
    """情节事件."""

    type: Literal["plot_event"] = "plot_event"
    event_subtype: Literal[
        "actor_arrival", "monster_attack", "faction_conflict", "quest_issue", "discovery"
    ] = "discovery"
    spawn_actors: list[dict] = Field(default_factory=list)
    spawn_scene: str | None = None
    affect_scene: str | None = None
    event_data: dict = Field(default_factory=dict)


class ActorMotivation(DMInstruction):
    """Actor 动机注入."""

    type: Literal["actor_motivation"] = "actor_motivation"
    target_actor_id: str = ""
    new_goal: str | None = None
    personality_shift: dict | None = None
    emotional_state: str | None = None


class SceneChange(DMInstruction):
    """场景变化."""

    type: Literal["scene_change"] = "scene_change"
    scene_id: str = ""
    weather: str | None = None
    time_of_day: str | None = None
    environmental_event: str | None = None


class SceneDirection(DMInstruction):
    """DM 导演指令."""

    type: Literal["scene_direction"] = "scene_direction"
    featured_pcs: list[str] = Field(default_factory=list)
    featured_actors: list[str] = Field(default_factory=list)
    actor_motivations: dict[str, str] = Field(default_factory=dict)
