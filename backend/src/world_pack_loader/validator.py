"""Pack 校验器——meta.yaml Pydantic schema + 关联引用校验 /
Pack validator — meta.yaml Pydantic schema + cross-referencing validation.

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


# ── 关联关系校验 / FK Validation ──


def validate_pack_relations(data: dict) -> list[str]:
    """校验 pack 内实体间的引用完整性，返回告警列表。

    检查项：
      - SceneObject.scene_id → Scene
      - PC/Actor.location.scene_id → Scene（含 fallback starting_scene）
      - PC/Actor.equipment.{weapon,armor,shield} → Item
      - PC/Actor.inventory[].item_id → Item
      - Scene.exits[].target → Scene
    """
    warnings: list[str] = []

    # ── 收集已声明 ID / Collect declared IDs ──
    scene_ids = {s.get("id") for s in data.get("scenes", []) if s.get("id")}
    item_ids = {i.get("id") for i in data.get("items", []) if i.get("id")}

    starting_scene = data.get("meta", {}).get("starting_scene", "scene_1")

    # 1. SceneObject.scene_id → Scene
    for obj in data.get("scene_objects", []):
        sid = obj.get("scene_id", "")
        if sid and sid not in scene_ids:
            warnings.append(f"SceneObject '{obj.get('id', '?')}' references unknown scene '{sid}'")

    # 2. Character location → Scene
    for pc in data.get("player_characters", []):
        sid = pc.get("scene_id") or starting_scene
        if sid not in scene_ids:
            warnings.append(f"PC '{pc.get('id', '?')}' (scene_id='{sid}') references unknown scene")

    for actor in data.get("actors", []):
        sid = actor.get("scene_id") or starting_scene
        if sid not in scene_ids:
            warnings.append(
                f"Actor '{actor.get('id', '?')}' (scene_id='{sid}') references unknown scene"
            )

    # 3. Equipment.{weapon, armor, shield} → Item
    for entity_list, label in [
        (data.get("player_characters", []), "PC"),
        (data.get("actors", []), "Actor"),
    ]:
        for entity in entity_list:
            equip = entity.get("equipment") or {}
            for slot, item_id in [
                ("weapon", equip.get("weapon")),
                ("armor", equip.get("armor")),
                ("shield", equip.get("shield")),
            ]:
                if item_id and item_id not in item_ids:
                    warnings.append(
                        f"{label} '{entity.get('id', '?')}' equipment.{slot} "
                        f"references unknown item '{item_id}'"
                    )

    # 4. Inventory[].item_id → Item
    for entity_list, label in [
        (data.get("player_characters", []), "PC"),
        (data.get("actors", []), "Actor"),
    ]:
        for entity in entity_list:
            for slot in entity.get("inventory") or []:
                if not isinstance(slot, dict):
                    continue
                item_id = slot.get("item") or slot.get("item_id")
                if item_id and item_id not in item_ids:
                    warnings.append(
                        f"{label} '{entity.get('id', '?')}' inventory "
                        f"references unknown item '{item_id}'"
                    )

    # 5. Scene.exits[] → Scene（互引校验）
    for s in data.get("scenes", []):
        for exit_ref in s.get("exits", []):
            if isinstance(exit_ref, dict):
                target = exit_ref.get("target") or exit_ref.get("scene_id", "")
            else:
                target = str(exit_ref)
            if target and target not in scene_ids:
                warnings.append(
                    f"Scene '{s.get('id', '?')}' exit references unknown scene '{target}'"
                )

    return warnings
