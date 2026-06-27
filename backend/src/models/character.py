"""PlayerCharacter and Actor Pydantic models.

Based on docs/06-data-layer.md §5.2, §5.2b.
Architecture spec §6.1 (PlayerCharacter), §6.2 (Actor).
"""

from enum import Enum

from pydantic import BaseModel, Field


# ---- Shared Types ----

class Attributes(BaseModel):
    strength: int = Field(default=10, alias="str")
    dexterity: int = Field(default=10, alias="dex")
    constitution: int = Field(default=10, alias="con")
    intelligence: int = Field(default=10, alias="int")
    wisdom: int = Field(default=10, alias="wis")
    charisma: int = Field(default=10, alias="cha")

    model_config = {"populate_by_name": True}


class CombatStats(BaseModel):
    hp: int
    max_hp: int
    ac: int = 10
    initiative: int = 0
    attack_bonus: int = 0
    damage_bonus: int = 0


class Location(BaseModel):
    scene_id: str
    position_x: int = 0
    position_y: int = 0


class Relationship(BaseModel):
    trust: float = 0.0  # -1.0 ~ 1.0
    interaction_count: int = 0


class InventorySlot(BaseModel):
    item_id: str  # 引用 Item.id
    qty: int = 1


class Equipment(BaseModel):
    """Character equipment slots, referencing Item ids."""

    weapon: str | None = None  # Item id (primary weapon)
    off_hand: str | None = None  # Item id (shield / secondary)
    armor: str | None = None  # Item id (armor)
    accessories: list[str] = Field(default_factory=list)  # Item id list


class CharacterArc(BaseModel):
    """PC character arc – drives deep decision-making."""

    growth_line: str = ""
    inner_conflict: str = ""
    destiny: str = ""


# ---- PlayerCharacter ----

class PlayerCharacter(BaseModel):
    """Main cast member (PC) – full character-arc-driven decision-making."""

    id: str
    name: str
    role: str  # fighter / rogue / cleric / wizard
    race: str | None = None
    status: str = "active"  # active / dead / left
    location: Location = Field(default_factory=lambda: Location(scene_id=""))
    attributes: Attributes = Field(default_factory=Attributes)
    combat: CombatStats = Field(default_factory=lambda: CombatStats(hp=10, max_hp=10))
    character_arc: CharacterArc = Field(default_factory=CharacterArc)
    long_term_goal: str = ""
    values: list[str] = Field(default_factory=list)
    personality: str = ""
    equipment: Equipment = Field(default_factory=Equipment)
    inventory: list[InventorySlot] = Field(default_factory=list)
    memory_count: int = 0
    importance_accumulator: float = 0.0
    reflection_threshold: int = 100
    relationships: dict[str, Relationship] = Field(default_factory=dict)
    joined_tick: int = 0
    roster_status: str = "member"  # member / departed


# ---- Actor ----

class ActorFunction(str, Enum):
    MERCHANT = "merchant"
    BYSTANDER = "bystander"
    DIALOGUE = "dialogue"
    QUEST_GIVER = "quest_giver"
    ENEMY = "enemy"
    ALLY = "ally"
    INFO_SOURCE = "info_source"


class Actor(BaseModel):
    """Supporting character – function-tag + DM-motivation-driven shallow decisions."""

    id: str
    name: str
    role: str
    race: str | None = None
    status: str = "active"  # active / dead / inactive
    location: Location = Field(default_factory=lambda: Location(scene_id=""))
    attributes: Attributes = Field(default_factory=Attributes)
    combat: CombatStats | None = None
    personality: str = ""
    functions: list[ActorFunction] = Field(default_factory=list)
    function_data: dict = Field(default_factory=dict)
    equipment: Equipment | None = None
    inventory: list[InventorySlot] = Field(default_factory=list)
    memory_count: int = 0
    importance_accumulator: float = 0.0
    reflection_threshold: int = 200
    relationships: dict[str, Relationship] = Field(default_factory=dict)
    dm_assigned: bool = False
    motivation_injected: str | None = None
    service_arcs: list[str] = Field(default_factory=list)
