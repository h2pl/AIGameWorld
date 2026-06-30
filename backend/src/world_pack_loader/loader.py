"""World Pack 加载器 / World Pack Loader.

从 Studio 生成的 world-pack（实例 YAML 合集）加载到运行存储：
  YAML → Pydantic 领域模型 → Repository → DB

术语 / Terminology:
  world-template = Studio 的 templates/ 下原始 YAML 蓝图（字段骨架）
  world-pack     = aw-studio generate 输出的实例 YAML 合集（含填充值的完整世界包）
"""

import logging
from pathlib import Path

from ..repository.character_repo import CharacterRepo
from ..repository.item_repo import ItemRepo
from ..repository.scene_repo import SceneRepo
from ..repository.story_repo import StoryRepo
from ..storage.chroma_client import ChromaClient
from ..storage.sqlite_client import SQLiteClient
from .deserialize import (
    actor_from_yaml,
    hook_from_yaml,
    item_from_yaml,
    pc_from_yaml,
    scene_obj_from_yaml,
    story_arc_from_yaml,
)
from .reader import read_pack
from .validator import validate_pack_relations

logger = logging.getLogger(__name__)


class WorldLoader:
    """加载 world-pack → AIGameWorld 存储（全部通过 Repo 层）."""

    def __init__(self, db: SQLiteClient, chroma: ChromaClient | None = None):
        self._chroma = chroma
        self._scene_repo = SceneRepo(db)
        self._item_repo = ItemRepo(db)
        self._char_repo = CharacterRepo(db)
        self._story_repo = StoryRepo(db)

    async def load(self, pack_dir: Path) -> dict[str, int]:
        """加载 world-pack 到数据库。

        world-pack = aw-studio generate 输出的实例 YAML 合集

        Args:
            pack_dir: world-pack 目录 (如 worlds/custom/my_world)

        Returns:
            {entity_type: count} 写入计数
        """
        if not pack_dir.exists():
            raise FileNotFoundError(f"Pack directory not found: {pack_dir}")

        data = read_pack(pack_dir)

        # ── Pack 标识：pack_id 来自 meta.id，唯一关联字段 / pack_id from meta.id ──
        pack_id = data["meta"].get("id", pack_dir.name)
        pack_name = data["meta"].get("name", pack_dir.name)
        logger.info("[WorldLoader] pack_id=%s pack_name=%s", pack_id, pack_name)

        # ── 关联关系校验 / FK validation ──
        warnings = validate_pack_relations(data)
        for w in warnings:
            logger.warning("[WorldLoader] FK warning: %s", w)

        counts: dict[str, int] = {}

        # 按 FK 依赖顺序写入 / Write in FK dependency order
        counts["scenes"] = await self._write_scenes(data.get("scenes", []), pack_id, pack_name)
        counts["items"] = await self._write_items(data.get("items", []), pack_id, pack_name)
        counts["scene_objects"] = await self._write_scene_objects(data.get("scene_objects", []))
        counts["pcs"] = await self._write_pcs(data)
        counts["actors"] = await self._write_actors(data)
        counts["story_arcs"] = await self._write_story_arcs(data)
        counts["story_hooks"] = await self._write_story_hooks(data)

        # ChromaDB (可选 / optional) — collection 用 pack_id 标识
        if self._chroma:
            self._write_lore_chroma(data.get("lore", []), pack_id)
            self._write_scenes_chroma(data.get("scenes", []), pack_id)

        return counts

    # ── Scenes (SceneRepo) ──

    async def _write_scenes(self, scenes: list[dict], pack_id: str, pack_name: str) -> int:
        for s in scenes:
            await self._scene_repo.save_scene(s, pack_id, pack_name)
        return len(scenes)

    # ── Items (ItemRepo) ──

    async def _write_items(self, items: list[dict], pack_id: str, pack_name: str) -> int:
        for i in items:
            await self._item_repo.save(item_from_yaml(i, pack_id, pack_name))
        return len(items)

    # ── Scene Objects (SceneRepo) ──

    async def _write_scene_objects(self, objects: list[dict]) -> int:
        for o in objects:
            await self._scene_repo.save_object(scene_obj_from_yaml(o))
        return len(objects)

    # ── PCs (CharacterRepo) ──

    async def _write_pcs(self, data: dict) -> int:
        starting_scene = data.get("meta", {}).get("starting_scene", "scene_1")
        pcs = data.get("player_characters", [])
        for pc_data in pcs:
            await self._char_repo.save_pc(pc_from_yaml(pc_data, starting_scene))
        return len(pcs)

    # ── Actors (CharacterRepo) ──

    async def _write_actors(self, data: dict) -> int:
        starting_scene = data.get("meta", {}).get("starting_scene", "scene_1")
        actors = data.get("actors", [])
        for a_data in actors:
            await self._char_repo.save_actor(actor_from_yaml(a_data, starting_scene))
        return len(actors)

    # ── Story (StoryRepo) ──

    async def _write_story_arcs(self, data: dict) -> int:
        arcs = data.get("story_setup", {}).get("story_arcs", [])
        for arc_data in arcs:
            await self._story_repo.save_arc(story_arc_from_yaml(arc_data))
        return len(arcs)

    async def _write_story_hooks(self, data: dict) -> int:
        hooks = data.get("story_setup", {}).get("story_hooks", [])
        for h_data in hooks:
            await self._story_repo.save_hook(hook_from_yaml(h_data))
        return len(hooks)

    # ── ChromaDB ──

    def _write_lore_chroma(self, lore_items: list[dict], pack_id: str) -> None:
        """灌入 lore 到 ChromaDB / Load lore into ChromaDB."""
        if not lore_items or not self._chroma:
            return
        collection = f"lore_{pack_id}"
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

    def _write_scenes_chroma(self, scenes: list[dict], pack_id: str) -> None:
        """灌入场景描述到 ChromaDB / Load scene descriptions into ChromaDB."""
        if not scenes or not self._chroma:
            return
        collection = f"scene_{pack_id}"
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
