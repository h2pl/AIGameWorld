"""故事摘要领域模型 / Story Summary Domain Model."""

from .base import DomainModel


class StorySummary(DomainModel):
    """故事摘要——每 N tick 异步压缩.

    summary_type:
    - "narrative": 事件摘要（基于 dm_narrative，记录发生了什么）
    - "scene": 场景摘要（基于 plot_brief，记录在哪、环境如何）
    """

    tick_start: int = 0
    tick_end: int = 0
    summary: str = ""
    summary_type: str = "narrative"
