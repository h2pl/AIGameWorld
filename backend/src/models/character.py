"""PlayerCharacter 和 Actor Pydantic 模型 / PlayerCharacter and Actor models.

基于 docs/06-data-layer.md §5.2, §5.2b / Based on docs/06-data-layer.md §5.2, §5.2b.
架构方案 §6.1 (PC), §6.2 (Actor) / Architecture spec §6.1, §6.2.
"""

from enum import Enum

from pydantic import BaseModel, Field


# ---- 共享类型 / Shared Types ----


class Attributes(BaseModel):
    """角色六维属性（D&D 对齐）/ Six core attributes (D&D-aligned).
    使用 alias 避免 Python 保留字冲突 / Aliases avoid Python reserved word clashes."""

    strength: int = Field(default=10, alias="str")       # 力量 / Strength
    dexterity: int = Field(default=10, alias="dex")       # 敏捷 / Dexterity
    constitution: int = Field(default=10, alias="con")    # 体质 / Constitution
    intelligence: int = Field(default=10, alias="int")    # 智力 / Intelligence
    wisdom: int = Field(default=10, alias="wis")          # 感知 / Wisdom
    charisma: int = Field(default=10, alias="cha")        # 魅力 / Charisma

    model_config = {"populate_by_name": True}  # 允许用别名或字段名构造


class CombatStats(BaseModel):
    """战斗属性 / Combat stats."""
    hp: int             # 当前生命值 / Current HP
    max_hp: int         # 最大生命值 / Max HP
    ac: int = 10        # 护甲等级 / Armor Class
    initiative: int = 0 # 先攻加值 / Initiative bonus
    attack_bonus: int = 0  # 攻击加值 / Attack bonus
    damage_bonus: int = 0  # 伤害加值 / Damage bonus


class Location(BaseModel):
    """角色位置 / Character location."""
    scene_id: str       # 所在场景 / Scene ID
    position_x: int = 0 # X 坐标
    position_y: int = 0 # Y 坐标


class Relationship(BaseModel):
    """角色间关系 / Inter-character relationship."""
    trust: float = 0.0              # 信任度 -1.0 ~ 1.0 / Trust level
    interaction_count: int = 0      # 交互次数 / Interaction count


class InventorySlot(BaseModel):
    """背包格子 / Inventory slot."""
    item_id: str    # 引用 Item.id / References Item.id
    qty: int = 1    # 数量 / Quantity


class Equipment(BaseModel):
    """装备槽位（引用 Item id）/ Equipment slots referencing Item ids."""
    weapon: str | None = None       # 主武器 / Primary weapon
    off_hand: str | None = None     # 副手（盾/副武器）/ Off-hand
    armor: str | None = None        # 护甲 / Armor
    accessories: list[str] = Field(default_factory=list)  # 饰品 / Accessories


class CharacterArc(BaseModel):
    """角色弧——驱动主角团深层决策 / Character arc — drives PC deep decisions."""
    growth_line: str = ""       # 成长线 / Growth trajectory
    inner_conflict: str = ""    # 内心冲突 / Inner conflict
    destiny: str = ""           # 命运走向 / Destiny


# ---- 主角团 PC / PlayerCharacter ----


class PlayerCharacter(BaseModel):
    """主角团成员——完整角色弧驱动决策 / Main cast member — full character-arc-driven decisions."""

    id: str
    name: str                       # 角色名 / Character name
    role: str                       # 职业: fighter/rogue/cleric/wizard
    race: str | None = None         # 种族 / Race
    status: str = "active"          # 状态: active/dead/left
    location: Location = Field(default_factory=lambda: Location(scene_id=""))
    attributes: Attributes = Field(default_factory=Attributes)
    combat: CombatStats = Field(default_factory=lambda: CombatStats(hp=10, max_hp=10))
    character_arc: CharacterArc = Field(default_factory=CharacterArc)
    long_term_goal: str = ""        # 长期目标（驱动决策）/ Long-term goal
    values: list[str] = Field(default_factory=list)  # 价值观（影响抉择）/ Values
    personality: str = ""
    equipment: Equipment = Field(default_factory=Equipment)
    inventory: list[InventorySlot] = Field(default_factory=list)  # 背包 / Backpack
    memory_count: int = 0           # ChromaDB 记忆总数 / Memory count
    importance_accumulator: float = 0.0  # 反思触发累计值 / Reflection accumulator
    reflection_threshold: int = 100     # 反思阈值（低=频繁）/ Reflection threshold
    relationships: dict[str, Relationship] = Field(default_factory=dict)
    joined_tick: int = 0            # 加入花名册的 tick
    roster_status: str = "member"   # 花名册状态: member/departed


# ---- 配角 Actor ----


class ActorFunction(str, Enum):
    """Actor 功能标签 / Actor function tags."""
    MERCHANT = "merchant"           # 商人
    BYSTANDER = "bystander"         # 纯路人
    DIALOGUE = "dialogue"           # 对话角色
    QUEST_GIVER = "quest_giver"     # 任务发布者
    ENEMY = "enemy"                 # 敌人
    ALLY = "ally"                   # 盟友
    INFO_SOURCE = "info_source"     # 信息源


class Actor(BaseModel):
    """配角——功能标签 + DM 动机驱动浅层决策 / Supporting character — function-tag + DM-motivation driven."""

    id: str
    name: str
    role: str
    race: str | None = None
    status: str = "active"          # active/dead/inactive
    location: Location = Field(default_factory=lambda: Location(scene_id=""))
    attributes: Attributes = Field(default_factory=Attributes)
    combat: CombatStats | None = None  # 路人可无战斗属性 / May be None for bystanders
    personality: str = ""
    functions: list[ActorFunction] = Field(default_factory=list)     # 功能标签
    function_data: dict = Field(default_factory=dict)                # 按功能存的扩展数据 / Per-function data
    equipment: Equipment | None = None     # 装备（敌人掉落源/商人货架）/ Equipment
    inventory: list[InventorySlot] = Field(default_factory=list)     # 背包 / Inventory
    memory_count: int = 0
    importance_accumulator: float = 0.0
    reflection_threshold: int = 200       # 反思阈值（高=更少反思）/ Higher = less frequent
    relationships: dict[str, Relationship] = Field(default_factory=dict)
    dm_assigned: bool = False             # DM 本步是否指定出场
    motivation_injected: str | None = None  # DM 注入的动机 / DM-injected motivation
    service_arcs: list[str] = Field(default_factory=list)  # 服务于哪些 StoryArc
