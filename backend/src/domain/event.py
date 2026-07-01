"""7 种事件类型 + Event Union / 7 event types + Event union."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SceneObject(BaseModel):
    """scene_objects 内的场景物品."""

    id: str
    name: str
    object_type: Literal["container", "door", "landmark"]
    position_x: int
    position_y: int


class ExploreRoll(BaseModel):
    """character_explore 的 D20 检定."""

    success: bool
    total: int
    dc: int
    critical: bool | None = None
    fumble: bool | None = None


class OpeningEvent(BaseModel):
    """DM 开场白."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["opening"] = "opening"
    text: str


class DmNarrativeEvent(BaseModel):
    """DM 叙事文本."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["dm_narrative"] = "dm_narrative"
    text: str
    mood: Literal["neutral", "tense", "hopeful", "ominous", "mysterious"] | None = None


class SceneSetupEvent(BaseModel):
    """加载场景."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["scene_setup"] = "scene_setup"
    scene_id: str
    scene_name: str


class SceneObjectsEvent(BaseModel):
    """加载场景物品."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["scene_objects"] = "scene_objects"
    scene_id: str
    objects: list[SceneObject] = Field(default_factory=list)


class CharacterMoveEvent(BaseModel):
    """角色移动到目标格."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["character_move"] = "character_move"
    character_id: str
    x: int
    y: int
    reasoning: str | None = None


class CharacterTalkEvent(BaseModel):
    """角色对话."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["character_talk"] = "character_talk"
    character_id: str
    dialogue: str
    target_id: str | None = None


class CharacterExploreEvent(BaseModel):
    """角色探索/交互，含 D20 检定."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["character_explore"] = "character_explore"
    character_id: str
    action: str
    target_id: str | None = None
    roll: ExploreRoll | None = None
    detail: str | None = None


Event = (
    OpeningEvent
    | DmNarrativeEvent
    | SceneSetupEvent
    | SceneObjectsEvent
    | CharacterMoveEvent
    | CharacterTalkEvent
    | CharacterExploreEvent
)

# 事件播放顺序 / Event playback sequence
SEQUENCE: list[str] = [
    "opening",
    "scene_setup",
    "scene_objects",
    "character_move",
    "character_talk",
    "character_explore",
    "dm_narrative",
]
