"""ChromaManager — ChromaDB 记忆/Lore 存储 / ChromaDB memory and lore storage.

基于 docs/06-data-layer.md §6 / Based on docs/06-data-layer.md §6.
Collection 分层设计 / Collection architecture:
- lore_{pack}       — 世界设定集（地理/历史/种族）/ World lore
- mem_{char_id}     — 角色长期记忆 / Character long-term memory
- reflect_{char_id} — 角色反思洞察 / Character reflection insights
- dm_narrative_{pack} — DM 叙事历史 / DM narrative history
- dm_summary_{pack}  — DM 事件摘要 / DM event summary
"""

from pathlib import Path

import chromadb
from chromadb.config import Settings


class ChromaManager:
    """管理 PC/Actor/DM 记忆和 Lore 的 ChromaDB 集合 / Manages ChromaDB collections."""

    def __init__(self, persist_path: str | Path):
        self.client = chromadb.PersistentClient(
            path=str(persist_path),
            settings=Settings(anonymized_telemetry=False),
        )

    # ---- 世界设定 / Lore ----

    def lore_collection(self, pack_name: str) -> chromadb.Collection:
        """获取或创建 Lore 集合 / Get or create Lore collection."""
        return self.client.get_or_create_collection(
            f"lore_{pack_name}", metadata={"type": "lore"}
        )

    def query_lore(self, pack_name: str, query: str, top_k: int = 3) -> list[dict]:
        """语义检索 Lore（空集合返回空列表）/ Semantic search Lore."""
        col = self.lore_collection(pack_name)
        if col.count() == 0:
            return []
        res = col.query(query_texts=[query], n_results=top_k)
        return [
            {"text": d, "meta": m}
            for d, m in zip(res["documents"][0], res["metadatas"][0])
        ]

    # ---- 角色记忆 / Character Memory ----

    def char_mem_collection(self, character_id: str) -> chromadb.Collection:
        """获取或创建角色记忆集合 / Get or create character memory collection."""
        return self.client.get_or_create_collection(
            f"mem_{character_id}",
            metadata={"type": "character_memory", "character_id": character_id},
        )

    def add_memory(self, character_id: str, mem_id: str, text: str, metadata: dict) -> None:
        """追加一条记忆 / Add a memory entry."""
        col = self.char_mem_collection(character_id)
        col.add(ids=[mem_id], documents=[text], metadatas=[metadata])

    def query_memory(
        self, character_id: str, query: str, top_k: int = 5, where: dict | None = None
    ) -> list[dict]:
        """语义检索角色记忆 / Semantic search character memories."""
        col = self.char_mem_collection(character_id)
        if col.count() == 0:
            return []
        res = col.query(query_texts=[query], n_results=top_k, where=where)
        return [
            {"text": d, "meta": m}
            for d, m in zip(res["documents"][0], res["metadatas"][0])
        ]

    # ---- 角色反思 / Character Reflection ----

    def char_reflect_collection(self, character_id: str) -> chromadb.Collection:
        """获取或创建反思集合 / Get or create reflection collection."""
        return self.client.get_or_create_collection(
            f"reflect_{character_id}",
            metadata={"type": "character_reflection", "character_id": character_id},
        )

    def add_reflection(self, character_id: str, reflect_id: str, text: str, metadata: dict) -> None:
        """追加一条反思 / Add a reflection entry."""
        col = self.char_reflect_collection(character_id)
        col.add(ids=[reflect_id], documents=[text], metadatas=[metadata])

    def query_reflections(self, character_id: str, query: str, top_k: int = 3) -> list[dict]:
        """检索反思洞察 / Search reflection insights."""
        col = self.char_reflect_collection(character_id)
        if col.count() == 0:
            return []
        res = col.query(query_texts=[query], n_results=top_k)
        return [
            {"text": d, "meta": m}
            for d, m in zip(res["documents"][0], res["metadatas"][0])
        ]

    # ---- DM 记忆 / DM Memory ----

    def dm_narrative_collection(self, pack_name: str) -> chromadb.Collection:
        """DM 叙事历史集合 / DM narrative history collection."""
        return self.client.get_or_create_collection(
            f"dm_narrative_{pack_name}", metadata={"type": "dm_narrative"}
        )

    def dm_summary_collection(self, pack_name: str) -> chromadb.Collection:
        """DM 事件摘要集合（每 N 步压缩）/ DM event summary collection."""
        return self.client.get_or_create_collection(
            f"dm_summary_{pack_name}", metadata={"type": "dm_summary"}
        )

    # ---- 生命周期 / Lifecycle ----

    def drop_character(self, character_id: str) -> None:
        """角色死亡/卸载时删除其记忆+反思集合 / Drop all character collections."""
        for suffix in ["mem", "reflect"]:
            name = f"{suffix}_{character_id}"
            try:
                self.client.delete_collection(name)
            except ValueError:
                pass

    def drop_pack(self, pack_name: str) -> None:
        """切换 World Pack 时删除 Lore + DM 集合 / Drop lore + DM collections."""
        for name in [
            f"lore_{pack_name}",
            f"dm_narrative_{pack_name}",
            f"dm_summary_{pack_name}",
        ]:
            try:
                self.client.delete_collection(name)
            except ValueError:
                pass
