"""Player Character 领域模型 / PC Domain Model."""

from .base import DomainModel


class PlayerCharacter(DomainModel):
    """Player Character——受玩家控制."""

    id: str
    name: str = ""
    role: str = ""
    race: str | None = None
    status: str = "active"
    scene_id: str = ""
    position_x: int = 0
    position_y: int = 0
    attributes_json: str = "{}"
    combat_json: str = "{}"
    character_arc_json: str = "{}"
    long_term_goal: str = ""
    values_json: str = "[]"
    personality: str = ""
    equipment_json: str = "{}"
    inventory_json: str = "[]"
    memory_count: int = 0
    importance_accumulator: float = 0.0
    relationships_json: str = "{}"
    joined_tick: int = 0
    roster_status: str = "member"
