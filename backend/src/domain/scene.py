"""场景领域模型 / Scene Domain Model."""

from .base import DomainModel


class Scene(DomainModel):
    """场景——世界中的一个地点."""

    id: str
    name: str = ""
    type: str = ""  # outdoor / indoor / underground
    description: str = ""
    spawn_x: int = 0  # 初始出生点 X / Spawn point X
    spawn_y: int = 0  # 初始出生点 Y / Spawn point Y
