"""事件领域模型 / Event Domain Model.

事件是每 tick 内产生的结构化记录，通过 message_id 关联一条消息，写入 tick_events 表。
所有事件共享同一结构：type + tick + payload dict，不区分子类型。
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class TickEventType(StrEnum):
    """事件类型枚举 / Event type enum."""

    DM_CREATE = "dm_create"
    SCENE_SETUP = "scene_setup"
    PC_TALK = "pc_talk"
    PC_INTERACT = "pc_interact"
    DM_NARRATIVE = "dm_narrative"


class TickEvent(BaseModel):
    """通用事件——type 标识类型，payload 承载具体数据."""

    type: TickEventType
    tick: int
    tick_message_id: str = ""
    payload: dict = Field(default_factory=dict)


# 事件播放顺序 / Event playback sequence
TICK_EVENT_SEQUENCE: list[str] = [e.value for e in TickEventType]

# 向后兼容别名 / Backward-compatible aliases
Event = TickEvent
SEQUENCE = TICK_EVENT_SEQUENCE
