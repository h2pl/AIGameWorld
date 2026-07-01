"""DM 产出记录领域模型 / DM Record Domain Model."""

from pydantic import BaseModel


class DMRecord(BaseModel):
    """DM 产出记录——每 tick 一行."""

    world_id: str = ""
    tick: int = 0
    plot_brief: str = ""
    hints: list[str] = []
    dm_narrative: str = ""
    ext: dict = {}
