"""World Pack 加载器 / World Pack Loader.

从 Studio 生成的 world-pack（实例 YAML 合集）加载到运行存储：
  YAML → Pydantic 领域模型 → Repository → DB

术语 / Terminology:
  world-template = Studio 的 templates/ 下原始 YAML 蓝图（字段骨架）
  world-pack     = aw-studio generate 输出的实例 YAML 合集（含填充值的完整世界包）
"""

from pathlib import Path

import yaml

from ..domain import (
    Actor,
    Attributes,
    CharacterArc,
    CombatStats,
    Equipment,
    InventorySlot,
    Item,
    ItemType,
    Location,
    PlayerCharacter,
    SceneObject,
    SceneObjectType,
    StoryArc,
    StoryHook,
)
from ..repository.character_repo import CharacterRepo
from ..repository.item_repo import ItemRepo
from ..repository.scene_repo import SceneRepo
from ..repository.story_repo import StoryRepo
from ..storage.chroma_client import ChromaClient
from ..storage.sqlite_client import SQLiteClient

# ═══════════════════════════════════════════════════════════════
# YAML → Domain Model 反序列化 / YAML → Domain Model deserialization
# ═══════════════════════════════════════════════════════════════


def _pc_from_yaml(data: dict, starting_scene: str) -> PlayerCharacter:
    """YAML dict → PlayerCharacter."""
    return PlayerCharacter(
        id=data.get("id", ""),
        name=data.get("name", ""),
        role=data.get("role", ""),
        race=data.get("race"),
        location=Location(scene_id=data.get("scene_id") or starting_scene),
        attributes=_attrs_from_yaml(data.get("attributes")),
        combat=_combat_from_yaml(data.get("combat")),
        personality=data.get("personality", ""),
        character_arc=_char_arc_from_yaml(data.get("character_arc")),
        long_term_goal=(data.get("character_arc") or {}).get("goal", ""),
        equipment=_equip_from_yaml(data.get("equipment")),
        inventory=_inventory_from_yaml(data.get("inventory")),
    )


def _actor_from_yaml(data: dict) -> Actor:
    """YAML dict → Actor."""
    return Actor(
        id=data.get("id", ""),
        name=data.get("name", ""),
        role=data.get("role", ""),
        race=data.get("race"),
        location=Location(scene_id=data.get("scene_id", "")),
        attributes=_attrs_from_yaml(data.get("attributes")),
        combat=_combat_from_yaml(data.get("combat")),
        personality=data.get("personality", ""),
        functions=data.get("functions", []),
        function_data=data.get("function_data", {}),
        equipment=_equip_from_yaml(data.get("equipment")),
        inventory=_inventory_from_yaml(data.get("inventory")),
    )


def _item_from_yaml(data: dict, pack_name: str) -> Item:
    """YAML dict → Item."""
    return Item(
        id=data.get("id", ""),
        name=data.get("name", ""),
        item_type=ItemType(data.get("item_type", "misc")),
        rarity=data.get("rarity", "common"),
        weight=data.get("weight", 0.0),
        value=data.get("value", 0),
        description=data.get("description", ""),
        data=data.get("data", {}),
        pack_name=pack_name,
    )


def _scene_obj_from_yaml(data: dict) -> SceneObject:
    """YAML dict → SceneObject."""
    return SceneObject(
        id=data.get("id", ""),
        name=data.get("name", ""),
        object_type=SceneObjectType(data.get("object_type", "decoration")),
        scene_id=data.get("scene_id", ""),
        interactable=data.get("interactable", True),
        interact_data=data.get("interact_data"),
    )


def _story_arc_from_yaml(data: dict) -> StoryArc:
    """YAML dict → StoryArc."""
    return StoryArc(
        id=data.get("id", f"arc_{data.get('title', '')}"),
        type=data.get("type", "main"),
        title=data.get("title", ""),
        stage=data.get("stage", "hook"),
        main_cast=data.get("main_cast", []),
        status="setup",
    )


def _hook_from_yaml(data: dict) -> StoryHook:
    """YAML dict → StoryHook."""
    return StoryHook(
        id=data.get("id", f"hook_{hash(data.get('description', ''))}"),
        description=data.get("description", ""),
        urgency=_urgency(data.get("urgency", "medium")),
    )


# ── 子结构 / Sub-structures ──


def _attrs_from_yaml(data: dict | None) -> Attributes:
    if not data:
        return Attributes()
    return Attributes(
        strength=data.get("str", data.get("strength", 10)),
        dexterity=data.get("dex", data.get("dexterity", 10)),
        constitution=data.get("con", data.get("constitution", 10)),
        intelligence=data.get("int", data.get("intelligence", 10)),
        wisdom=data.get("wis", data.get("wisdom", 10)),
        charisma=data.get("cha", data.get("charisma", 10)),
    )


def _combat_from_yaml(data: dict | None) -> CombatStats | None:
    if not data:
        return None
    return CombatStats(
        hp=data.get("hp", 10),
        max_hp=data.get("max_hp", data.get("hp", 10)),
        ac=data.get("ac", 10),
        attack_bonus=data.get("attack_bonus", 0),
        damage_dice=data.get("damage_dice", "1d4"),
    )


def _char_arc_from_yaml(data: dict | None) -> CharacterArc:
    """YAML dict → CharacterArc."""
    if not data:
        return CharacterArc()
    return CharacterArc(
        stage=data.get("stage", "setup"),
        description=data.get("description", ""),
    )


def _equip_from_yaml(data: dict | None) -> Equipment:
    if not data:
        return Equipment()
    return Equipment(
        weapon_id=data.get("weapon"),
        armor_id=data.get("armor"),
        shield_id=data.get("shield"),
    )


def _inventory_from_yaml(data: list | None) -> list[InventorySlot]:
    if not data:
        return []
    return [
        InventorySlot(
            item_id=i.get("item", i.get("item_id", "")), quantity=i.get("qty", i.get("quantity", 1))
        )
        for i in data
    ]


def _urgency(text: str) -> int:
    return {"low": 3, "medium": 5, "high": 8}.get(text, 5)


# ═══════════════════════════════════════════════════════════════
# YAML 文件读取 / YAML file reading
# ═══════════════════════════════════════════════════════════════


def _read_pack(pack_dir: Path) -> dict:
    """读取 world-pack 目录下所有实例 YAML → dict."""
    result: dict = {
        "meta": {},
        "lore": [],
        "scenes": [],
        "player_characters": [],
        "actors": [],
        "items": [],
        "scene_objects": [],
        "story_setup": {"arcs": [], "hooks": []},
    }
    if not pack_dir.exists():
        return result

    _read_single(pack_dir / "meta.yaml", result, "meta")
    _read_dir(pack_dir / "lore", result, "lore")
    _read_dir(pack_dir / "scenes", result, "scenes")
    _read_dir(pack_dir / "player_characters", result, "player_characters")
    _read_dir(pack_dir / "actors", result, "actors")
    _read_dir(pack_dir / "items", result, "items")
    _read_dir(pack_dir / "scene_objects", result, "scene_objects")
    _read_single(pack_dir / "story_setup.yaml", result, "story_setup")

    return result


def _read_single(filepath: Path, result: dict, key: str) -> None:
    if filepath.exists():
        data = yaml.safe_load(filepath.read_text(encoding="utf-8")) or {}
        result[key] = data


def _read_dir(dirpath: Path, result: dict, key: str) -> None:
    if not dirpath.exists():
        return
    for yf in sorted(dirpath.glob("*.yaml")):
        data = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
        result[key].append(data)


# ═══════════════════════════════════════════════════════════════
# WorldLoader
# ═══════════════════════════════════════════════════════════════


class WorldLoader:
    """加载 world-pack → AIGameWorld 存储（全部通过 Repo 层）."""

    def __init__(self, db: SQLiteClient, chroma: ChromaClient | None = None):
        self._chroma = chroma
        self._scene_repo = SceneRepo(db)
        self._item_repo = ItemRepo(db)
        self._char_repo = CharacterRepo(db)
        self._story_repo = StoryRepo(db)

    async def load(self, pack_dir: Path, pack_name: str = "") -> dict[str, int]:
        """加载 world-pack 到数据库。

        world-pack = aw-studio generate 输出的实例 YAML 合集

        Args:
            pack_dir: world-pack 目录 (如 worlds/custom/my_world)
            pack_name: Pack 名称 (默认取目录名)

        Returns:
            {entity_type: count} 写入计数
        """
        if not pack_dir.exists():
            raise FileNotFoundError(f"Pack directory not found: {pack_dir}")
        if not pack_name:
            pack_name = pack_dir.name

        data = _read_pack(pack_dir)
        counts: dict[str, int] = {}

        # 按 FK 依赖顺序写入 / Write in FK dependency order
        counts["scenes"] = await self._write_scenes(data.get("scenes", []), pack_name)
        counts["items"] = await self._write_items(data.get("items", []), pack_name)
        counts["scene_objects"] = await self._write_scene_objects(data.get("scene_objects", []))
        counts["pcs"] = await self._write_pcs(data)
        counts["actors"] = await self._write_actors(data.get("actors", []))
        counts["story_arcs"] = await self._write_story_arcs(data)
        counts["story_hooks"] = await self._write_story_hooks(data)

        # ChromaDB (可选 / optional)
        if self._chroma:
            self._write_lore_chroma(data.get("lore", []), pack_name)
            self._write_scenes_chroma(data.get("scenes", []), pack_name)

        return counts

    # ── Scenes (SceneRepo) ──

    async def _write_scenes(self, scenes: list[dict], pack_name: str) -> int:
        for s in scenes:
            await self._scene_repo.save_scene(s, pack_name)
        return len(scenes)

    # ── Items (ItemRepo) ──

    async def _write_items(self, items: list[dict], pack_name: str) -> int:
        for i in items:
            await self._item_repo.save(_item_from_yaml(i, pack_name))
        return len(items)

    # ── Scene Objects (SceneRepo) ──

    async def _write_scene_objects(self, objects: list[dict]) -> int:
        for o in objects:
            await self._scene_repo.save_object(_scene_obj_from_yaml(o))
        return len(objects)

    # ── PCs (CharacterRepo) ──

    async def _write_pcs(self, data: dict) -> int:
        starting_scene = data.get("meta", {}).get("starting_scene", "scene_1")
        pcs = data.get("player_characters", [])
        for pc_data in pcs:
            await self._char_repo.save_pc(_pc_from_yaml(pc_data, starting_scene))
        return len(pcs)

    # ── Actors (CharacterRepo) ──

    async def _write_actors(self, actors: list[dict]) -> int:
        for a_data in actors:
            await self._char_repo.save_actor(_actor_from_yaml(a_data))
        return len(actors)

    # ── Story (StoryRepo) ──

    async def _write_story_arcs(self, data: dict) -> int:
        arcs = data.get("story_setup", {}).get("arcs", [])
        for arc_data in arcs:
            await self._story_repo.save_arc(_story_arc_from_yaml(arc_data))
        return len(arcs)

    async def _write_story_hooks(self, data: dict) -> int:
        hooks = data.get("story_setup", {}).get("hooks", [])
        for h_data in hooks:
            await self._story_repo.save_hook(_hook_from_yaml(h_data))
        return len(hooks)

    # ── ChromaDB ──

    def _write_lore_chroma(self, lore_items: list[dict], pack_name: str) -> None:
        """灌入 lore 到 ChromaDB / Load lore into ChromaDB."""
        if not lore_items or not self._chroma:
            return
        collection = f"lore_{pack_name}"
        for lore in lore_items:
            content = lore.get("content", "")
            chunks = _chunk_text(content)
            for i, chunk in enumerate(chunks):
                self._chroma.add(
                    collection=collection,
                    ids=[f"{lore.get('id', '')}_{i}"],
                    documents=[chunk],
                    metadatas=[
                        {
                            "lore_id": lore.get("id", ""),
                            "category": lore.get("category", ""),
                            "chunk": i,
                        }
                    ],
                )

    def _write_scenes_chroma(self, scenes: list[dict], pack_name: str) -> None:
        """灌入场景描述到 ChromaDB / Load scene descriptions into ChromaDB."""
        if not scenes or not self._chroma:
            return
        collection = f"scene_{pack_name}"
        for s in scenes:
            self._chroma.add(
                collection=collection,
                ids=[s.get("id", "")],
                documents=[s.get("description", "")],
                metadatas=[
                    {
                        "scene_id": s.get("id", ""),
                        "name": s.get("name", ""),
                        "type": s.get("type", ""),
                    }
                ],
            )


def _chunk_text(text: str, chunk_size: int = 256) -> list[str]:
    """按段落切分，小段合并 / Split by paragraphs, merge small ones."""
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for p in paragraphs:
        if current_len + len(p) > chunk_size and current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(p)
        current_len += len(p)
    if current:
        chunks.append("\n\n".join(current))
    return chunks
