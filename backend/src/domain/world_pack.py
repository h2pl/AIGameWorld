"""世界包领域模型 / World Pack Domain Model."""

from pydantic import BaseModel


class WorldPack(BaseModel):
    """一个 world-pack 的元信息，字段对齐 meta.yaml."""

    id: str
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    rule_set: str = "dnd_5e_srd"
    author: str = ""
    license: str = "MIT"
    starting_scene: str = ""
