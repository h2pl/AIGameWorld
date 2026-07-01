"""事件领域模型 / Event Domain Model.

事件是每 tick 内产生的结构化记录，通过 message_id 关联一条消息，写入 events 表。
所有事件共享同一结构：type + tick + payload dict，不区分子类型。
"""

from pydantic import BaseModel, Field


class Event(BaseModel):
    """通用事件——type 标识类型，payload 承载具体数据."""

    type: str
    tick: int
    payload: dict = Field(default_factory=dict)


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
