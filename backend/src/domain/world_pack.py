"""世界包领域模型 / World Pack Domain Model."""

from pydantic import BaseModel, Field


class WorldPack(BaseModel):
    """一个 world-pack 的元信息 / Metadata for a world-pack."""

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    rule_set: str = "dnd_5e_srd"
    author: str = ""
    license: str = "MIT"
    theme: str = ""  # 主题/世界观主题 / Theme/world theme
    starting_scene: str = ""
