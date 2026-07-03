"""World Pack 加载器 / World Pack Loader.

从 Studio 生成的 world-pack（实例 YAML 合集）加载到运行存储：
  YAML → Pydantic 领域模型 → Repository → DB

术语 / Terminology:
  world-template = Studio 的 templates/ 下原始 YAML 蓝图（字段骨架）
  world-pack     = aw-studio generate 输出的实例 YAML 合集（含填充值的完整世界包）
"""

from pathlib import Path

from src.repository.pc_repo import PcRepo

from ..domain.world import World
from ..repository.item_repo import ItemRepo
from ..repository.scene_repo import SceneRepo
from ..repository.world_repo import WorldRepo
from ..storage.chroma_client import ChromaClient
from ..storage.sqlite_client import SQLiteClient
from ..utils.logging import get_logger
from . import deserialize, reader, validator

logger = get_logger(__name__)


class WorldLoader:
    """加载 world-pack → AIGameWorld 存储（全部通过 Repo 层）."""

    def __init__(self, db: SQLiteClient, chroma: ChromaClient | None = None):
        self._chroma = chroma
        self._world_repo = WorldRepo(db)
        self._scene_repo = SceneRepo(db)
        self._item_repo = ItemRepo(db)
        self._pc_repo = PcRepo(db)

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

        data = reader.read_pack(pack_dir)

        # ── Pack 标识：world_id 来自 meta.id，唯一关联字段 / world_id from meta.id ──
        world_id = data["meta"].get("id", pack_dir.name)
        world_name = data["meta"].get("name", pack_dir.name)
        logger.info("[WorldLoader] world_id=%s world_name=%s", world_id, world_name)

        # ── 创建 world / Create world ──
        meta = data["meta"]
        await self._world_repo.create(
            World(
                id=world_id,
                name=world_name,
                description=meta.get("description", ""),
                version=meta.get("version", "1.0.0"),
                rule_set=meta.get("rule_set", "dnd_5e_srd"),
                author=meta.get("author", ""),
                starting_scene=meta.get("starting_scene", ""),
            )
        )

        # ── 关联关系校验 / FK validation ──
        warnings = validator.validate_pack_relations(data)
        for w in warnings:
            logger.warning("[WorldLoader] FK warning: %s", w)

        counts: dict[str, int] = {}

        # 按 FK 依赖顺序写入 / Write in FK dependency order
        counts["scenes"] = await self._write_scenes(data.get("scenes", []), world_id)
        counts["items"] = await self._write_items(data.get("items", []), world_id)
        counts["scene_objects"] = await self._write_scene_objects(
            data.get("scene_objects", []), world_id
        )
        counts["pcs"] = await self._write_pcs(data, world_id)
        counts["actors"] = await self._write_actors(data, world_id)

        # ChromaDB (可选 / optional) — collection 用 world_id 标识
        if self._chroma:
            self._write_lore_chroma(data.get("lore", []), world_id)
            self._write_scenes_chroma(data.get("scenes", []), world_id)

        return counts

    # ── Scenes (SceneRepo) ──

    async def _write_scenes(self, scenes: list[dict], world_id: str) -> int:
        for s in scenes:
            await self._scene_repo.save_scene(s, world_id)
        return len(scenes)

    # ── Items (ItemRepo) ──

    async def _write_items(self, items: list[dict], world_id: str) -> int:
        for i in items:
            await self._item_repo.save(deserialize.item_from_yaml(i, world_id))
        return len(items)

    # ── Scene Objects (SceneRepo) ──

    async def _write_scene_objects(self, objects: list[dict], world_id: str) -> int:
        for o in objects:
            await self._scene_repo.save_object(deserialize.scene_obj_from_yaml(o, world_id))
        return len(objects)

    # ── PCs (PcRepo) ──

    async def _write_pcs(self, data: dict, world_id: str) -> int:
        starting_scene = data.get("meta", {}).get("starting_scene", "scene_1")
        pcs = data.get("player_characters", [])
        for pc_data in pcs:
            await self._pc_repo.save_pc(deserialize.pc_from_yaml(pc_data, starting_scene, world_id))
        return len(pcs)

    # ── Actors (PcRepo) ──

    async def _write_actors(self, data: dict, world_id: str) -> int:
        starting_scene = data.get("meta", {}).get("starting_scene", "scene_1")
        actors = data.get("actors", [])
        for a_data in actors:
            await self._pc_repo.save_actor(
                deserialize.actor_from_yaml(a_data, starting_scene, world_id)
            )
        return len(actors)

    # ── ChromaDB ──

    def _write_lore_chroma(self, lore_items: list[dict], world_id: str) -> None:
        """灌入 lore 到 ChromaDB / Load lore into ChromaDB."""
        if not lore_items or not self._chroma:
            return
        collection = f"lore_{world_id}"
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

    def _write_scenes_chroma(self, scenes: list[dict], world_id: str) -> None:
        """灌入场景描述到 ChromaDB / Load scene descriptions into ChromaDB."""
        if not scenes or not self._chroma:
            return
        collection = f"scene_{world_id}"
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
