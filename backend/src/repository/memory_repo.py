"""记忆仓储 / Memory Repository.

基于 ChromaDB（长期/反思）+ 内存 deque（短期），对齐 design/04-agent-layer.md §8 + 06-data-layer.md §6.
"""

from collections import deque
from uuid import uuid4

from ..domain.memory import Memory
from ..storage.chroma_client import ChromaClient

_MEM_PREFIX = "mem_{character_id}"
_REFLECT_PREFIX = "reflect_{character_id}"


class MemoryRepo:
    """角色记忆存取——短期(deque) + 长期(ChromaDB) + 反思(ChromaDB)."""

    def __init__(self, chroma: ChromaClient):
        self._chroma = chroma
        self._short_term: dict[str, deque[Memory]] = {}  # character_id → 最近10条

    # ── 短期记忆 / Short-term ──
    def _short_queue(self, character_id: str) -> deque[Memory]:
        if character_id not in self._short_term:
            self._short_term[character_id] = deque(maxlen=10)
        return self._short_term[character_id]

    # ── 存储 / Store ──

    def store(self, character_id: str, content: str, tick: int, importance: int = 2) -> Memory:
        """存储新记忆（短期 + 长期）."""
        mem = Memory(
            id=f"mem_{character_id}_{tick}_{uuid4().hex[:6]}",
            character_id=character_id,
            content=content,
            tick=tick,
            importance=importance,
        )
        self._short_queue(character_id).append(mem)
        col_name = _MEM_PREFIX.format(character_id=character_id)
        self._chroma.add(
            collection=col_name,
            ids=[mem.id],
            documents=[content],
            metadatas=[{"tick": tick, "importance": importance, "type": "observation"}],
        )
        return mem

    def store_reflection(self, character_id: str, insight: str, tick: int) -> Memory:
        """存储反思洞察（重要性=10）."""
        mem_id = f"reflect_{character_id}_{tick}_{uuid4().hex[:6]}"
        col_name = _REFLECT_PREFIX.format(character_id=character_id)
        self._chroma.add(
            collection=col_name,
            ids=[mem_id],
            documents=[insight],
            metadatas=[{"tick": tick, "importance": 10, "type": "reflection"}],
        )
        return Memory(
            id=mem_id,
            character_id=character_id,
            content=insight,
            tick=tick,
            importance=10,
            memory_type="reflection",
        )

    # ── 检索 / Retrieve ──

    def retrieve(self, character_id: str, query: str, top_k: int = 5) -> list[Memory]:
        """检索相关记忆（短期全量 + 长期语义 Top-K）."""
        short = list(self._short_queue(character_id))
        col_name = _MEM_PREFIX.format(character_id=character_id)
        results = self._chroma.query(collection=col_name, query_text=query, top_k=top_k)
        long_term = [
            Memory(
                id=r["meta"].get("id", ""),
                character_id=character_id,
                content=r["text"],
                tick=r["meta"].get("tick", 0),
                importance=r["meta"].get("importance", 1),
            )
            for r in results
        ]
        # 合并去重（按 id），按重要性降序
        seen = {m.id for m in short}
        merged = list(short)
        for m in long_term:
            if m.id not in seen:
                merged.append(m)
                seen.add(m.id)
        merged.sort(key=lambda m: m.importance, reverse=True)
        return merged[:top_k]

    def retrieve_reflections(self, character_id: str, query: str, top_k: int = 3) -> list[Memory]:
        """检索反思记忆."""
        col_name = _REFLECT_PREFIX.format(character_id=character_id)
        results = self._chroma.query(collection=col_name, query_text=query, top_k=top_k)
        return [
            Memory(
                id=r["meta"].get("id", ""),
                character_id=character_id,
                content=r["text"],
                tick=r["meta"].get("tick", 0),
                importance=10,
                memory_type="reflection",
            )
            for r in results
        ]

    # ── 生命周期 / Lifecycle ──

    def drop_character(self, character_id: str) -> None:
        """删除角色所有记忆."""
        self._short_term.pop(character_id, None)
        for prefix in [_MEM_PREFIX, _REFLECT_PREFIX]:
            self._chroma.delete_collection(prefix.format(character_id=character_id))

    def importance_should_reflect(
        self,
        character_id: str,
        threshold: int = 100,
    ) -> bool:
        """检查重要性累计是否超阈值."""
        recent = list(self._short_queue(character_id))
        total = sum(m.importance for m in recent)
        return total >= threshold

    def count(self, character_id: str) -> int:
        """返回某角色的总记忆数（短期）."""
        return len(self._short_queue(character_id))
