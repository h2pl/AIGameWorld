"""DM 产出记录领域模型 / DM Record Domain Model."""

from .base import DomainModel


class DMRecord(DomainModel):
    """DM 产出记录——每 tick 一行，承载 dm_create 全部信息."""

    tick: int = 0
    plot_brief: str = ""
    hints: list[str] = []
    dm_narrative: str = ""
    ext: dict = {}
    scene_id: str = ""
