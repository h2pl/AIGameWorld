"""ChromaManager – ChromaDB memory/lore storage.

Based on docs/06-data-layer.md §6.
"""

from pathlib import Path

import chromadb
from chromadb.config import Settings


class ChromaManager:
    """Manages ChromaDB collections for PC/Actor/DM memory and Lore."""

    def __init__(self, persist_path: str | Path):
        self.client = chromadb.PersistentClient(
            path=str(persist_path),
            settings=Settings(anonymized_telemetry=False),
        )

    # ---- Lore ----
    def lore_collection(self, pack_name: str) -> chromadb.Collection:
        return self.client.get_or_create_collection(
            f"lore_{pack_name}", metadata={"type": "lore"}
        )

    def query_lore(self, pack_name: str, query: str, top_k: int = 3) -> list[dict]:
        col = self.lore_collection(pack_name)
        if col.count() == 0:
            return []
        res = col.query(query_texts=[query], n_results=top_k)
        return [
            {"text": d, "meta": m}
            for d, m in zip(res["documents"][0], res["metadatas"][0])
        ]

    # ---- Character memory ----
    def char_mem_collection(self, character_id: str) -> chromadb.Collection:
        return self.client.get_or_create_collection(
            f"mem_{character_id}",
            metadata={"type": "character_memory", "character_id": character_id},
        )

    def add_memory(
        self, character_id: str, mem_id: str, text: str, metadata: dict
    ) -> None:
        col = self.char_mem_collection(character_id)
        col.add(ids=[mem_id], documents=[text], metadatas=[metadata])

    def query_memory(
        self, character_id: str, query: str, top_k: int = 5, where: dict | None = None
    ) -> list[dict]:
        col = self.char_mem_collection(character_id)
        if col.count() == 0:
            return []
        res = col.query(query_texts=[query], n_results=top_k, where=where)
        return [
            {"text": d, "meta": m}
            for d, m in zip(res["documents"][0], res["metadatas"][0])
        ]

    # ---- Character reflection ----
    def char_reflect_collection(self, character_id: str) -> chromadb.Collection:
        return self.client.get_or_create_collection(
            f"reflect_{character_id}",
            metadata={"type": "character_reflection", "character_id": character_id},
        )

    def add_reflection(
        self, character_id: str, reflect_id: str, text: str, metadata: dict
    ) -> None:
        col = self.char_reflect_collection(character_id)
        col.add(ids=[reflect_id], documents=[text], metadatas=[metadata])

    def query_reflections(
        self, character_id: str, query: str, top_k: int = 3
    ) -> list[dict]:
        col = self.char_reflect_collection(character_id)
        if col.count() == 0:
            return []
        res = col.query(query_texts=[query], n_results=top_k)
        return [
            {"text": d, "meta": m}
            for d, m in zip(res["documents"][0], res["metadatas"][0])
        ]

    # ---- DM memory ----
    def dm_narrative_collection(self, pack_name: str) -> chromadb.Collection:
        return self.client.get_or_create_collection(
            f"dm_narrative_{pack_name}", metadata={"type": "dm_narrative"}
        )

    def dm_summary_collection(self, pack_name: str) -> chromadb.Collection:
        return self.client.get_or_create_collection(
            f"dm_summary_{pack_name}", metadata={"type": "dm_summary"}
        )

    # ---- Lifecycle ----
    def drop_character(self, character_id: str) -> None:
        """Drop all collections for a character (memory + reflection)."""
        for suffix in ["mem", "reflect"]:
            name = f"{suffix}_{character_id}"
            try:
                self.client.delete_collection(name)
            except ValueError:
                pass

    def drop_pack(self, pack_name: str) -> None:
        """Drop Lore + DM collections when switching World Packs."""
        for name in [
            f"lore_{pack_name}",
            f"dm_narrative_{pack_name}",
            f"dm_summary_{pack_name}",
        ]:
            try:
                self.client.delete_collection(name)
            except ValueError:
                pass
