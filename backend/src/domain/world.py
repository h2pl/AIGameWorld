"""World——由 world_pack 导入生成，承载全部元信息 / World imported from world_pack."""

from pydantic import BaseModel


class World(BaseModel):
    id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    rule_set: str = "dnd_5e_srd"
    author: str = ""
    starting_scene: str = ""
