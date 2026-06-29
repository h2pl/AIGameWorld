"""Pack 校验器——meta.yaml Pydantic schema / Pack validator — meta.yaml Pydantic schema.

基于 docs/05-world-pack-layer.md §4 / Based on docs/05-world-pack-layer.md §4.
"""

from pydantic import BaseModel, Field


class SpriteConfig(BaseModel):
    """精灵图配置 / Sprite configuration."""

    frame_size: int = 48  # 帧尺寸（像素）/ Frame size (pixels)
    directions: int = 4  # 方向数 / Direction count
    frames_per_direction: int = 4  # 每方向帧数 / Frames per direction


class FilesManifest(BaseModel):
    """Pack 文件清单（加载器按此校验完整性）/ Pack file manifest (loader validates against this)."""

    lore: list[str] = Field(default_factory=list)
    scenes: list[str] = Field(default_factory=list)
    player_characters: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    items: list[str] = Field(default_factory=list)
    scene_objects: list[str] = Field(default_factory=list)
    story_setup: str = "story_setup.yaml"


class StartingPc(BaseModel):
    """起始主角团规格 / Starting PC specification."""

    template: str  # 模板 ID / Template ID
    name: str | None = None  # 覆盖名字 / Name override


class StartingActor(BaseModel):
    """起始 Actor 规格 / Starting Actor specification."""

    template: str  # 模板 ID / Template ID
    count: int = 1  # 实例数量 / Instance count
    name_override: str | list[str] | None = None  # 覆盖名字 / Name override


class StartingSceneObject(BaseModel):
    """起始场景对象规格 / Starting SceneObject specification."""

    template: str  # 模板 ID / Template ID
    scene: str  # 放置到哪个场景 / Target scene
    position: dict = Field(default_factory=lambda: {"x": 0, "y": 0})  # 位置


class MetaYaml(BaseModel):
    """meta.yaml Pydantic schema——Pack 入口文件 / meta.yaml schema — Pack entry point."""

    id: str = Field(
        pattern=r"^[a-z][a-z0-9_]*$"
    )  # 唯一 ID，必须匹配目录名 / Must match directory name
    name: str = ""  # 显示名 / Display name
    description: str = ""  # 描述 / Description
    version: str = "1.0.0"  # Pack 版本 / Pack version
    rule_set: str = "dnd_5e_srd"  # 规则集版本 / Rule set version
    author: str = ""  # 作者 / Author
    license: str = "MIT"  # 许可证 / License
    files: FilesManifest = Field(default_factory=FilesManifest)  # 文件清单
    sprites: SpriteConfig = Field(default_factory=SpriteConfig)  # 精灵配置
    starting_scene: str = ""  # 默认起始场景
    starting_pcs: list[StartingPc] = Field(default_factory=list)  # 起始 PC
    starting_actors: list[StartingActor] = Field(default_factory=list)  # 起始 Actor
    starting_scene_objects: list[StartingSceneObject] = Field(default_factory=list)  # 起始场景对象


class PackValidator:
    """校验 meta.yaml / Validate meta.yaml against Pydantic schema."""

    @staticmethod
    def validate(data: dict) -> MetaYaml:
        """校验并返回 MetaYaml 实例 / Validate and return MetaYaml instance."""
        return MetaYaml(**data)
