"""场景领域模型 / Scene Domain Model."""

from pydantic import Field

from .base import DomainModel


class Scene(DomainModel):
    """场景——世界中的一个地点，同时作为 tick 内的场景上下文."""

    id: str
    name: str = ""
    type: str = ""  # outdoor / indoor / underground
    description: str = ""
    spawn_x: int = 0  # 初始出生点 X / Spawn point X
    spawn_y: int = 0  # 初始出生点 Y / Spawn point Y
    map_key: str = ""
    map_width: int = Field(default=40, ge=1)
    map_height: int = Field(default=40, ge=1)
    tilemap_summary: str = ""
    landmarks: list[dict] = Field(default_factory=list)
    exits: list[dict] = Field(default_factory=list)
