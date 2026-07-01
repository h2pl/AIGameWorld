"""NPC Actor 领域模型 / Actor (NPC) Domain Model."""

from .base import DomainModel


class Actor(DomainModel):
    """NPC Actor——AI 控制."""

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
    personality: str = ""
    functions_json: str = "[]"
    function_data_json: str = "{}"
    equipment_json: str = "{}"
    inventory_json: str = "[]"
    memory_count: int = 0
    importance_accumulator: float = 0.0
    relationships_json: str = "{}"
    dm_assigned: bool = False
    motivation_injected: str | None = None
