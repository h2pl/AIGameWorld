"""Player Character 领域模型 / PC Domain Model."""

import json

from pydantic import model_validator

from .base import DomainModel


class PlayerCharacter(DomainModel):
    """Player Character——受玩家控制 / Player-controlled character."""

    id: str  # 唯一标识 / Unique ID
    name: str = ""  # 角色名 / Character name
    role: str = ""  # 职业 / Class (fighter/rogue/cleric/wizard)
    race: str | None = None  # 种族 / Race
    status: str = "active"  # 状态 / Status
    scene_id: str = ""  # 所在场景 / Current scene
    position_x: int = 0  # X 坐标 / X coordinate
    position_y: int = 0  # Y 坐标 / Y coordinate
    attributes_json: str = "{}"  # 属性 / Attributes
    combat_json: str = "{}"  # 战斗数据 / Combat stats
    arc_json: str = "{}"  # 角色弧 / Character arc
    long_term_goal: str = ""  # 长期目标 / Long-term goal
    values_json: str = "[]"  # 价值观 / Core values
    personality: str = ""  # 性格 / Personality
    equipment_json: str = "{}"  # 装备 / Equipment
    inventory_json: str = "[]"  # 背包 / Inventory
    memory_count: int = 0  # 记忆条数 / Memory count
    importance_accumulator: float = 0.0  # 重要性累计 / Importance accumulator
    relationships_json: str = "{}"  # 关系 / Relationships
    joined_tick: int = 0  # 加入 tick / Joined tick
    roster_status: str = "member"  # 花名册状态 / Roster status

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
        if "arc" in data and not data.get("arc_json"):
            data["arc_json"] = json.dumps(data.pop("arc"), ensure_ascii=False)
        return data
