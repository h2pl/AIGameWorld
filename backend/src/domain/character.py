"""角色领域模型 / Character Domain Models — 完整版."""

from pydantic import BaseModel, Field


# ============================================================
# 值对象 / Value Objects
# ============================================================
class Location(BaseModel):
    """位置 / Location."""

    scene_id: str = ""
    position_x: int = 0
    position_y: int = 0


class CombatStats(BaseModel):
    """战斗属性（DND-style stats）/ Combat stats (DND-style)."""

    hp: int = 10
    max_hp: int = 10
    ac: int = 10
    initiative: int = 0
    speed: int = 30
    attack_bonus: int = 0
    damage_dice: str = "1d4"


class Attributes(BaseModel):
    """六维属性 / Six core attributes."""

    model_config = {"populate_by_name": True}

    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10


class Equipment(BaseModel):
    """装备 / Equipment."""

    weapon_id: str | None = None
    armor_id: str | None = None
    shield_id: str | None = None
    accessory_id: str | None = None


class InventorySlot(BaseModel):
    """背包槽位 / Inventory slot."""

    item_id: str = ""
    quantity: int = 1


class Relationship(BaseModel):
    """角色关系 / Character relationship."""

    attitude: str = "neutral"  # friendly / neutral / hostile
    description: str = ""


class CharacterArc(BaseModel):
    """角色弧 / Character arc."""

    stage: str = "setup"  # setup / growth / crisis / resolution
    progress: float = 0.0
    description: str = ""


# ============================================================
# 实体 / Entities
# ============================================================
class Actor(BaseModel):
    """NPC Actor——AI 控制."""

    id: str
    name: str = ""
    role: str = ""  # merchant / guard / quest_giver / villager
    race: str | None = None
    status: str = "active"
    location: Location = Field(default_factory=Location)
    attributes: Attributes = Field(default_factory=Attributes)
    combat: CombatStats | None = None
    personality: str = ""
    functions: list[str] = Field(default_factory=list)
    function_data: dict = Field(default_factory=dict)
    equipment: Equipment | None = None
    inventory: list[InventorySlot] = Field(default_factory=list)
    memory_count: int = 0
    importance_accumulator: float = 0.0
    relationships: dict[str, Relationship] = Field(default_factory=dict)
    dm_assigned: bool = False
    motivation_injected: str | None = None
    service_arcs: list[str] = Field(default_factory=list)
    world_id: str = ""


class PlayerCharacter(BaseModel):
    """Player Character——受玩家控制."""

    id: str
    name: str = ""
    role: str = ""
    race: str | None = None
    status: str = "active"
    location: Location = Field(default_factory=Location)
    attributes: Attributes = Field(default_factory=Attributes)
    combat: CombatStats = Field(default_factory=CombatStats)
    character_arc: CharacterArc = Field(default_factory=CharacterArc)
    long_term_goal: str = ""
    values: list[str] = Field(default_factory=list)
    personality: str = ""
    equipment: Equipment = Field(default_factory=Equipment)
    inventory: list[InventorySlot] = Field(default_factory=list)
    memory_count: int = 0
    importance_accumulator: float = 0.0
    relationships: dict[str, Relationship] = Field(default_factory=dict)
    joined_tick: int = 0
    roster_status: str = "member"
    world_id: str = ""
