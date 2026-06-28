"""角色记忆仓储——知道 collection 命名规则，调 ChromaClient 裸操作."""

import uuid

from ..storage.chroma_client import ChromaClient


class MemoryRepo:
    """角色记忆存取."""

    def __init__(self, chroma: ChromaClient, character_id: str):
        self._chroma = chroma
        self._char_id = character_id

    def add_interaction(self, text: str, importance: int = 1, metadata: dict | None = None) -> None:
        mem_id = f"mem_{self._char_id}_{uuid.uuid4().hex[:8]}"
        meta = metadata or {}
        meta["importance"] = importance
        self._chroma.add(f"mem_{self._char_id}", [mem_id], [text], [meta])

    def recall(self, query: str, top_k: int = 5) -> list[dict]:
        return self._chroma.query(f"mem_{self._char_id}", query, top_k)

    def add_reflection(self, text: str, metadata: dict | None = None) -> None:
        reflect_id = f"reflect_{self._char_id}_{uuid.uuid4().hex[:8]}"
        self._chroma.add(f"reflect_{self._char_id}", [reflect_id], [text], [metadata or {}])

    def recall_reflections(self, query: str, top_k: int = 3) -> list[dict]:
        return self._chroma.query(f"reflect_{self._char_id}", query, top_k)

    def clear(self) -> None:
        self._chroma.delete_collection(f"mem_{self._char_id}")
        self._chroma.delete_collection(f"reflect_{self._char_id}")
