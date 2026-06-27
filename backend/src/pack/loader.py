"""WorldLoader — 从 YAML 加载 World Pack 到 WorldState / Load World Pack YAML into WorldState.

基于 docs/05-world-pack-layer.md §9 / Based on docs/05-world-pack-layer.md.
加载顺序 / Load order:
  1. meta.yaml 校验 / Validate meta.yaml
  2. Lore → ChromaDB / Pump lore into ChromaDB
  3. 场景定义 / Scene definitions
  4. PC 模板 → 实例化 / PC templates → instantiate
  5. Actor 模板 → 实例化 / Actor templates → instantiate
  6. Item 物品定义 / Item definitions
  7. SceneObject 场景对象 / Scene objects
  8. story_setup 初始剧情 / Initial story setup
"""

import json
from pathlib import Path

import yaml

from src.models import (
    Actor, Attributes, CharacterArc, CombatStats, Equipment,
    InventorySlot, Item, ItemType, Location,
    PlayerCharacter, Scene, SceneObject, SceneObjectType, StoryArc, StoryHook, WorldState,
)
from src.storage import ChromaManager
from .validator import PackValidator, MetaYaml


class WorldLoader:
    """加载 World Pack 目录到 WorldState 和 ChromaDB / Loads a World Pack into WorldState + ChromaDB."""

    def __init__(self, worlds_dir: Path, chroma: ChromaManager):
        self.worlds_dir = Path(worlds_dir)
        self.chroma = chroma

    # TODO(M4): async def / Make async for M4
    def load(self, pack_name: str) -> WorldState:
        """主入口：加载 Pack 返回 WorldState / Main entry: load Pack and return WorldState."""
        pack_dir = self.worlds_dir / pack_name
        if not pack_dir.exists():
            raise FileNotFoundError(f"World Pack 未找到: {pack_dir}")

        meta = self._load_meta(pack_dir)
        self._validate_rule_set(meta.rule_set)
        self.pump_lore(pack_dir, pack_name)

        return WorldState(
            tick=0,
            current_world=pack_name,
            current_scene=meta.starting_scene,
            scenes=self._load_scenes(pack_dir, meta),
            player_characters=self._load_pc_instances(pack_dir, meta),
            actors=self._load_actor_instances(pack_dir, meta),
            items=self._load_items(pack_dir, meta),
            scene_objects=self._load_scene_objects(pack_dir, meta),
            story_arcs=self._load_story_arcs(pack_dir, meta),
            story_hooks=self._load_story_hooks(pack_dir, meta),
        )

    def _validate_rule_set(self, rule_set: str) -> None:
        if rule_set not in {"dnd_5e_srd"}:
            raise ValueError(f"Unsupported: {rule_set}")

    def _load_meta(self, pack_dir: Path) -> MetaYaml:
        """加载并校验 meta.yaml / Load and validate meta.yaml."""
        path = pack_dir / "meta.yaml"
        if not path.exists():
            raise FileNotFoundError(f"meta.yaml 未找到: {pack_dir}")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return PackValidator.validate(data)

    # ---- Lore（灌入 ChromaDB）/ Lore pumped into ChromaDB ----

    # TODO(M2): behaviors/ dir / TODO(M8): assets/ dir
    def pump_lore(self, pack_dir: Path, pack_name: str) -> None:
        """解析 lore/*.yaml 灌入 ChromaDB / Parse lore/*.yaml into ChromaDB."""
        lore_dir = pack_dir / "lore"
        if not lore_dir.exists():
            return
        collection = self.chroma.lore_collection(pack_name)
        for yaml_file in lore_dir.glob("*.yaml"):
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            for key, value in data.items():
                text = yaml.dump({key: value}, allow_unicode=True, sort_keys=False)
                chunk_id = f"{yaml_file.stem}_{key}"
                collection.add(ids=[chunk_id], documents=[text], metadatas=[{"source": yaml_file.name, "section": key}])

    # ---- 场景 / Scenes ----

    def _load_scenes(self, pack_dir: Path, meta: MetaYaml) -> dict[str, Scene]:
        """加载场景定义 / Load scene definitions."""
        scenes = {}
        for rel_path in meta.files.scenes:
            data = yaml.safe_load((pack_dir / rel_path).read_text(encoding="utf-8"))
            for entry in (data if isinstance(data, list) else [data]):
                scenes[entry["id"]] = Scene(
                    id=entry["id"], name=entry.get("name", ""),
                    type=entry.get("type", "village"),
                    description=entry.get("description", ""),
                    exits=entry.get("exits", []),
                    landmarks=entry.get("landmarks", []),
                    environment=entry.get("environment", {}),
                    pack_name=meta.id,
                )
        return scenes

    # ---- PC 实例 / PC Instances ----

    def _load_pc_instances(self, pack_dir: Path, meta: MetaYaml) -> dict[str, PlayerCharacter]:
        """从模板实例化起始主角团 / Instantiate starting PCs from templates."""
        templates = self._load_pc_templates(pack_dir, meta)
        pcs = {}
        for spec in meta.starting_pcs:
            tpl = templates[spec.template]
            name = spec.name or tpl.get("name", spec.template)
            pc_id = name.lower().replace(" ", "_")
            arc = tpl.get("character_arc", {})
            eq = tpl.get("equipment", {})
            inv = tpl.get("inventory", [])
            pcs[pc_id] = PlayerCharacter(
                id=pc_id, name=name, role=tpl.get("role", ""),
                race=tpl.get("race"), status="active",
                location=Location(scene_id=meta.starting_scene, position_x=0, position_y=0),
                attributes=Attributes.model_validate(tpl.get("attributes", {})),
                combat=CombatStats.model_validate(tpl.get("combat", {"hp": 10, "max_hp": 10})),
                character_arc=CharacterArc(
                    growth_line=arc.get("growth_line", ""),
                    inner_conflict=arc.get("inner_conflict", ""),
                    destiny=arc.get("destiny", ""),
                ),
                long_term_goal=tpl.get("long_term_goal", ""),
                values=tpl.get("values", []),
                personality=tpl.get("personality", ""),
                equipment=Equipment(
                    weapon=eq.get("weapon"), off_hand=eq.get("off_hand"),
                    armor=eq.get("armor"), accessories=eq.get("accessories", []),
                ),
                inventory=[InventorySlot(item_id=i["item"], qty=i.get("qty", 1)) for i in inv],
                relationships={},
                joined_tick=0, roster_status="member",
            )
        return pcs

    def _load_pc_templates(self, pack_dir: Path, meta: MetaYaml) -> dict[str, dict]:
        templates = {}
        for rel_path in meta.files.player_characters:
            data = yaml.safe_load((pack_dir / rel_path).read_text(encoding="utf-8"))
            for entry in (data if isinstance(data, list) else [data]):
                templates[entry["id"]] = entry
        return templates

    # ---- Actor 实例 / Actor Instances ----

    def _load_actor_instances(self, pack_dir: Path, meta: MetaYaml) -> dict[str, Actor]:
        """从模板实例化起始 Actor / Instantiate starting Actors from templates."""
        templates = self._load_actor_templates(pack_dir, meta)
        actors = {}
        for spec in meta.starting_actors:
            tpl = templates[spec.template]
            names = self._resolve_names(spec)
            for name in names:
                actor_id = name.lower().replace(" ", "_")
                eq = tpl.get("equipment", {}) or {}
                inv = tpl.get("inventory", [])
                combat = tpl.get("combat")
                actors[actor_id] = Actor(
                    id=actor_id, name=name, role=tpl.get("role", ""),
                    race=tpl.get("race"), status="active",
                    location=Location(scene_id=meta.starting_scene, position_x=0, position_y=0),
                    attributes=Attributes.model_validate(tpl.get("attributes", {})),
                    combat=CombatStats.model_validate(combat) if combat else None,
                    personality=tpl.get("personality", ""),
                    functions=tpl.get("functions", []),
                    function_data=tpl.get("function_data", {}),
                    equipment=Equipment(**{
                        k: eq[k] for k in ("weapon", "off_hand", "armor", "accessories") if k in eq
                    }) if eq else None,
                    inventory=[InventorySlot(item_id=i["item"], qty=i.get("qty", 1)) for i in inv],
                    relationships={},
                )
        return actors

    def _load_actor_templates(self, pack_dir: Path, meta: MetaYaml) -> dict[str, dict]:
        templates = {}
        for rel_path in meta.files.actors:
            data = yaml.safe_load((pack_dir / rel_path).read_text(encoding="utf-8"))
            for entry in (data if isinstance(data, list) else [data]):
                templates[entry["id"]] = entry
        return templates

    @staticmethod
    def _resolve_names(spec) -> list[str]:
        """解析 Actor 实例名（支持列表/单个/count 三种模式）/ Resolve Actor instance names."""
        if isinstance(spec.name_override, list):
            return spec.name_override
        if spec.name_override:
            return [spec.name_override]
        return [f"{spec.template}_{i + 1}" for i in range(spec.count)]

    # ---- 物品 / Items ----

    def _load_items(self, pack_dir: Path, meta: MetaYaml) -> dict[str, Item]:
        """加载全局物品定义 / Load global item definitions."""
        items = {}
        for rel_path in meta.files.items:
            data = yaml.safe_load((pack_dir / rel_path).read_text(encoding="utf-8"))
            entries = data.get("items", data if isinstance(data, list) else [])
            for entry in entries:
                items[entry["id"]] = Item(
                    id=entry["id"], name=entry.get("name", ""),
                    item_type=ItemType(entry["item_type"]),
                    rarity=entry.get("rarity", "common"),
                    weight=entry.get("weight", 0.0), value=entry.get("value", 0),
                    description=entry.get("description", ""),
                    data=entry.get("data", {}), pack_name=meta.id,
                )
        return items

    # ---- 场景对象 / Scene Objects ----

    def _load_scene_objects(self, pack_dir: Path, meta: MetaYaml) -> dict[str, SceneObject]:
        """加载场景对象（宝箱/门/陷阱等）/ Load scene objects (chests/doors/traps/etc.)."""
        templates = {}
        for rel_path in meta.files.scene_objects:
            data = yaml.safe_load((pack_dir / rel_path).read_text(encoding="utf-8"))
            entries = data.get("objects", data if isinstance(data, list) else [])
            for entry in entries:
                templates[entry["id"]] = entry

        objects = {}
        for spec in meta.starting_scene_objects:
            tpl = templates[spec.template]
            obj_id = f"{spec.scene}_{spec.template}"
            objects[obj_id] = SceneObject(
                id=obj_id, name=tpl.get("name", spec.template),
                object_type=SceneObjectType(tpl.get("object_type", "decoration")),
                scene_id=spec.scene,
                position_x=spec.position.get("x", 0),
                position_y=spec.position.get("y", 0),
                interactable=tpl.get("interactable", True),
                interact_data=tpl.get("interact_data"),
            )
        return objects

    # ---- 故事 / Story ----

    def _load_story_arcs(self, pack_dir: Path, meta: MetaYaml) -> list[StoryArc]:
        """加载初始剧情线 / Load initial story arcs."""
        setup = self._load_story_setup(pack_dir, meta)
        return [StoryArc(**arc) for arc in setup.get("story_arcs", [])]

    def _load_story_hooks(self, pack_dir: Path, meta: MetaYaml) -> list[StoryHook]:
        """加载初始伏笔 / Load initial story hooks."""
        setup = self._load_story_setup(pack_dir, meta)
        return [StoryHook(**hook) for hook in setup.get("story_hooks", [])]

    # TODO(M2): unload() via ChromaManager.drop_pack()
    def _load_story_setup(self, pack_dir: Path, meta: MetaYaml) -> dict:
        path = pack_dir / meta.files.story_setup
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text(encoding="utf-8"))
