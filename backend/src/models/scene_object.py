"""场景对象 Pydantic 模型 / SceneObject Pydantic model.

基于 docs/06-data-layer.md §5.2c / Based on docs/06-data-layer.md §5.2c.
架构方案 §6.10 (SceneObject) / Architecture spec §6.10.

场景对象是不能自主行动的场景实体 / Scene objects are non-autonomous scene entities.
与 Actor 的区分标准：能否自主决策 → Actor 或 PC；不能 → SceneObject。
Distinction from Actor: can make autonomous decisions → Actor/PC; cannot → SceneObject.
"""

from enum import Enum

from pydantic import BaseModel, Field


class SceneObjectType(str, Enum):
    """场景对象类型枚举 / Scene object type enum."""
    CONTAINER = "container"     # 宝箱/柜子/袋子 / Chest/cabinet/bag
    DOOR = "door"               # 门/栅栏/传送门 / Door/gate/portal
    TRAP = "trap"               # 陷阱 / Trap
    ANIMAL = "animal"           # 动物（无决策能力）/ Animal (no decision capability)
    MECHANISM = "mechanism"     # 机关/祭坛/控制台 / Mechanism/altar/console
    DECORATION = "decoration"   # 纯装饰（树/石头/路标）/ Pure decoration
    ITEM_DROP = "item_drop"     # 地上掉落的物品 / Dropped items on ground


class SceneObject(BaseModel):
    """场景中不能自主行动的实体——引用 Item id / Non-autonomous entity referencing Item ids.
    
    interact_data 按 object_type 存不同内容 / interact_data varies by object_type:
      CONTAINER: {locked, lock_dc, items: [{item_id, qty}]}
      DOOR:      {locked, key_id, leads_to}
      TRAP:      {trigger, damage, damage_type, detect_dc, disarm_dc, armed}
      ITEM_DROP: {item_id, qty}
      MECHANISM: {trigger_event, requires_item}
    """

    id: str
    name: str                       # 显示名 / Display name
    object_type: SceneObjectType    # 对象类型 / Object type
    scene_id: str = ""              # 所在场景 / Scene ID
    position_x: int = 0             # X 坐标
    position_y: int = 0             # Y 坐标
    interactable: bool = True       # 是否可交互 / Whether interactable
    interact_data: dict | None = None  # 交互数据（引用 Item id）/ Interaction data
