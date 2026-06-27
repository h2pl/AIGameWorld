"""物品系统 Pydantic 模型 / Item system Pydantic model.

基于 docs/06-data-layer.md §5.2b / Based on docs/06-data-layer.md §5.2b.
架构方案 §6.8 (Item 系统) / Architecture spec §6.8.

物品是最底层独立系统，被 PC/Actor/SceneObject 引用。
Items are the lowest-level independent system, referenced by PC/Actor/SceneObject.
"""

from enum import Enum

from pydantic import BaseModel, Field


class ItemType(str, Enum):
    """物品类型枚举 / Item type enum."""
    WEAPON = "weapon"           # 武器（剑/弓/法杖...）/ Weapon
    ARMOR = "armor"             # 护甲（皮甲/链甲/板甲...）/ Armor
    SHIELD = "shield"           # 盾牌 / Shield
    POTION = "potion"           # 药水（治疗/增益/解毒...）/ Potion
    SCROLL = "scroll"           # 卷轴 / Scroll
    KEY = "key"                 # 钥匙（开门用）/ Key
    CONSUMABLE = "consumable"   # 消耗品（食物/火把/绳索...）/ Consumable
    MISC = "misc"               # 杂项（宝石/书信/任务物品）/ Miscellaneous


class Item(BaseModel):
    """全局物品定义——被 PC/Actor/SceneObject 引用 / Global item definition referenced by entities.
    
    data 字段按 ItemType 存不同类型数据 / data field stores type-specific data:
      WEAPON: {damage_dice, damage_type, properties, attack_modifier}
      ARMOR:  {ac, dex_bonus_max, strength_required, stealth_disadvantage}
      SHIELD: {ac_bonus}
      POTION: {effect, potency, duration, useable_in_combat}
      KEY:    {opens: "door_id"}
    """

    id: str                         # 全局唯一 ID / Globally unique
    name: str                       # 显示名 / Display name
    item_type: ItemType             # 物品类型 / Item type
    rarity: str = "common"          # 稀有度: common/uncommon/rare/legendary/artifact
    weight: float = 0.0             # 重量（磅）/ Weight in pounds
    value: int = 0                  # 基础价格（金币）/ Base price in gold
    description: str = ""           # 描述文本 / Description
    data: dict = Field(default_factory=dict)  # 按类型存扩展数据 / Type-specific data
    pack_name: str = ""             # 来自哪个 World Pack / Source pack
