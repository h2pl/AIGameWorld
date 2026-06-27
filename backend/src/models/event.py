"""事件 Pydantic 模型 / Event Pydantic model.

基于 docs/06-data-layer.md §5.3 / Based on docs/06-data-layer.md §5.3.

Event Log 是追加写、永不修改的日志 / Event log is append-only, immutable.
"""

from pydantic import BaseModel, Field


class Event(BaseModel):
    """世界事件——追加写到 event_log，永不修改 / World event — appended to event_log, never modified."""

    id: str                         # evt_{tick}_{seq} 格式
    tick: int                       # 发生的 tick
    seq: int = 0                    # tick 内序列号 / Sequence within tick
    type: str                       # 事件类型: combat_hit/character_talk/scene_change/plot/...
    importance: int = 1             # 重要性: 1=普通 2=重要 3=关键 / 1=normal 2=important 3=critical
    source: str = "system"          # 来源角色 ID 或 "system" / Source character ID or "system"
    target: str | None = None       # 目标 / Target
    data: dict = Field(default_factory=dict)  # 事件负载 / Event payload
    narrative: str | None = None    # DM 生成的叙事片段（可选）/ Optional DM narrative snippet
