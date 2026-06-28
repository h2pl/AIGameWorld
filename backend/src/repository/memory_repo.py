"""角色记忆仓储 / Character Memory Repository."""

import uuid

from ..domain import PlayerCharacter, Actor
from ..storage.chroma_store import ChromaManager


class MemoryRepo:
    """角色记忆存取——每个 PC/Actor 独立 ChromaDB collection."""

    def __init__(self, chroma: ChromaManager, character_id: str):
        self._chroma = chroma
        self._character_id = character_id

    def add_interaction(self, text: str, importance: int = 1, metadata: dict | None = None) -> None:
        mem_id = f"mem_{self._character_id}_{uuid.uuid4().hex[:8]}"
        meta = metadata or {}
        meta["importance"] = importance
        self._chroma.add_memory(self._character_id, mem_id, text, meta)

    def recall(self, query: str, top_k: int = 5) -> list[dict]:
        return self._chroma.query_memory(self._character_id, query, top_k)

    def add_reflection(self, text: str, metadata: dict | None = None) -> None:
        reflect_id = f"reflect_{self._character_id}_{uuid.uuid4().hex[:8]}"
        self._chroma.add_reflection(self._character_id, reflect_id, text, metadata or {})

    def recall_reflections(self, query: str, top_k: int = 3) -> list[dict]:
        return self._chroma.query_reflections(self._character_id, query, top_k)

    def clear(self) -> None:
        self._chroma.drop_character(self._character_id)
