"""角色领域模型 / Character Domain Models."""
from pydantic import BaseModel, Field


# === DND 六维属性 ===
class Attributes(BaseModel):
    """角色基础属性（D20 修正值 = (stat - 10) // 2）"""
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10


# === 装备槽位 ===
class Equipment(BaseModel):
    weapon: str | None = None
    armor: str | None = None
    shield: str | None = None
    accessory: str | None = None


# === 角色基类 ===
class Character(BaseModel):
    """角色基类——PC 和 Actor 共享字段."""

    id: str
    name: str = ""
    character_type: str = "pc"               # "pc" | "actor"
    attributes: Attributes = Field(default_factory=Attributes)
    level: int = 1
    hp: int = 10
    max_hp: int = 10
    inventory: list[str] = Field(default_factory=list)   # Item ID 列表
    equipment: Equipment = Field(default_factory=Equipment)
    scene_id: str = ""                                   # 当前所在场景
    position_x: int = 0
    position_y: int = 0
    alive: bool = True
    pack_name: str = ""


# === PC（可扮演角色） ===
class PC(Character):
    """Player Character——受玩家控制、有角色弧."""

    character_type: str = "pc"
    backstory: str = ""                     # 背景故事
    personality: str = ""                   # 性格描述
    long_term_goal: str = ""                # 长期目标
    short_term_goal: str = ""               # 当前短期目标
    character_arc: str = ""                 # 角色弧阶段: setup / growth / crisis / resolution
    relationships: dict[str, str] = Field(default_factory=dict)  # character_id → 关系描述


# === Actor（NPC） ===
class Actor(Character):
    """Non-Player Actor——AI 控制、有功能标签."""

    character_type: str = "actor"
    role: str = ""                          # 功能角色: merchant / guard / quest_giver / villager
    personality: str = ""                   # 性格标签
    daily_schedule: list[str] = Field(default_factory=list)  # 每日作息
    faction: str = ""                       # 所属势力
    reputation: int = 50                    # 声望值 (0-100)
