"""CharacterMemoryStore: 角色记忆封装层 / Character memory abstraction layer.

基于 design/06-data-layer.md §8 / Based on data layer design.
封装 ChromaDB 的 add/recall/reflect 操作 / Wraps ChromaDB add/recall/reflect ops.
"""

import uuid

from src.storage.chroma_store import ChromaManager


class CharacterMemoryStore:
    """角色记忆管理 / Character memory manager.

    每个 PC/Actor 有独立的 ChromaDB collection / Each PC/Actor has independent collection.
    """

    def __init__(self, chroma: ChromaManager, character_id: str):
        self._chroma = chroma              # ChromaDB 管理器 / ChromaDB manager
        self._character_id = character_id  # 角色 ID / Character ID

    def add_interaction(self, text: str, importance: int = 1, metadata: dict | None = None) -> None:
        """添加一条交互到短期记忆 / Add an interaction to short-term memory.

        Args:
            text: 交互内容 / Interaction text
            importance: 重要性(0-10) / Importance score (0-10)
            metadata: 附加元数据 / Additional metadata
        """
        mem_id = f"mem_{self._character_id}_{uuid.uuid4().hex[:8]}"
        meta = metadata or {}
        meta["importance"] = importance
        self._chroma.add_memory(self._character_id, mem_id, text, meta)

    def recall(self, query: str, top_k: int = 5) -> list[dict]:
        """语义检索相关记忆 / Semantic recall of memories.
        
        Returns:
            list[dict]: [{"text": "...", "meta": {...}}, ...]
        """
        return self._chroma.query_memory(self._character_id, query, top_k)

    def add_reflection(self, text: str, metadata: dict | None = None) -> None:
        """添加反思到长期记忆 / Add reflection to long-term memory."""
        reflect_id = f"reflect_{self._character_id}_{uuid.uuid4().hex[:8]}"
        self._chroma.add_reflection(self._character_id, reflect_id, text, metadata or {})

    def recall_reflections(self, query: str, top_k: int = 3) -> list[dict]:
        """检索历史反思 / Recall past reflections.
        
        Returns:
            list[dict]: [{"text": "...", "meta": {...}}, ...]
        """
        return self._chroma.query_reflections(self._character_id, query, top_k)

    def clear(self) -> None:
        """清空该角色所有记忆 / Drop all character collections."""
        self._chroma.drop_character(self._character_id)
