"""Pack validator – Pydantic schema for meta.yaml validation.

Based on docs/05-world-pack-layer.md §4.
"""

from pydantic import BaseModel, Field


class SpriteConfig(BaseModel):
    frame_size: int = 48
    directions: int = 4
    frames_per_direction: int = 4


class FilesManifest(BaseModel):
    lore: list[str] = Field(default_factory=list)
    scenes: list[str] = Field(default_factory=list)
    player_characters: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    items: list[str] = Field(default_factory=list)
    scene_objects: list[str] = Field(default_factory=list)
    story_setup: str = "story_setup.yaml"


class StartingPc(BaseModel):
    template: str
    name: str | None = None


class StartingActor(BaseModel):
    template: str
    count: int = 1
    name_override: str | list[str] | None = None


class StartingSceneObject(BaseModel):
    template: str
    scene: str
    position: dict = Field(default_factory=lambda: {"x": 0, "y": 0})


class MetaYaml(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    rule_set: str = "dnd_5e_srd"
    author: str = ""
    license: str = "MIT"
    files: FilesManifest = Field(default_factory=FilesManifest)
    sprites: SpriteConfig = Field(default_factory=SpriteConfig)
    starting_scene: str = ""
    starting_pcs: list[StartingPc] = Field(default_factory=list)
    starting_actors: list[StartingActor] = Field(default_factory=list)
    starting_scene_objects: list[StartingSceneObject] = Field(default_factory=list)


class PackValidator:
    """Validates meta.yaml against Pydantic schema."""

    @staticmethod
    def validate(data: dict) -> MetaYaml:
        return MetaYaml(**data)
