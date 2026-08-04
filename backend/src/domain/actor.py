"""NPC Actor 领域模型 / Actor (NPC) Domain Model."""

import json

from pydantic import model_validator

from .base import DomainModel


class Actor(DomainModel):
    """NPC Actor——AI 控制."""

    id: str
    name: str = ""
    role: str = ""
    race: str | None = None
    status: str = "active"
    disposition: str = "neutral"  # neutral / friendly / hostile（NPC / 敌人 等）
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

    @model_validator(mode="before")
    @classmethod
    def _compat_legacy_fields(cls, data):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        if "location" in data and isinstance(data["location"], dict):
            data.setdefault("scene_id", data["location"].get("scene_id", ""))
            data.pop("location", None)
        if "attributes" in data and not data.get("attributes_json"):
            data["attributes_json"] = json.dumps(data.pop("attributes"), ensure_ascii=False)
        if "combat" in data and not data.get("combat_json"):
            data["combat_json"] = json.dumps(data.pop("combat"), ensure_ascii=False)
        return data
