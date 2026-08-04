"""World——由 world_pack 导入生成，承载全部元信息 / World imported from world_pack."""

from pydantic import BaseModel


class World(BaseModel):
    id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    rule_set: str = "dnd_5e_srd"
    author: str = ""
    starting_scene_id: str = ""  # world 关联初始场景 / world-associated starting scene
    current_scene_id: str = ""  # 世界当前主场景（party 每 tick 裁决后持久化）/ current main scene
    status: str = "init"  # 世界初始化状态：init（未初始化）→ ready（已初始化）
    data_tick: int = 0
    display_tick: int = 0
