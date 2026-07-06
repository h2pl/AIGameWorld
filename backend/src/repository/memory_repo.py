"""记忆仓储 / Memory Repository.

基于三层记忆架构：
- 短期：内存 deque（每角色最近 10 条 observation）
- 中期：SQLite `memories` 表（按角色/世界持久化）
- 长期：ChromaDB（语义检索 + 反思集合）

对齐 design/04-agent-layer.md §8 + 06-data-layer.md §6。
"""

from collections import deque
from uuid import uuid4

from ..schemas.memory_schema import Memory
from ..storage.chroma_client import ChromaClient
from ..utils.logging import get_logger

logger = get_logger(__name__)

_MEM_PREFIX = "mem_{pc_id}"
_REFLECT_PREFIX = "reflect_{pc_id}"


class MemoryRepo:
    """角色记忆存取——短期(deque) + 中期(SQLite) + 长期(ChromaDB) + 反思(ChromaDB)."""

    def __init__(self, chroma: ChromaClient, sqlite=None):
        self._chroma = chroma
        self._sqlite = sqlite
        self._short_term: dict[str, deque[Memory]] = {}  # pc_id → 最近10条
        self._table_ensured = False

    # ── 表初始化 / Table init ──
    async def initialize(self) -> None:
        """异步初始化 SQLite 表（如提供 sqlite）."""
        if self._sqlite and not self._table_ensured:
            await self._ensure_table()

    async def _ensure_table(self) -> None:
        await self._sqlite.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id          TEXT PRIMARY KEY,
                pc_id       TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                tick        INTEGER NOT NULL DEFAULT 0,
                importance  INTEGER NOT NULL DEFAULT 2,
                memory_type TEXT    NOT NULL DEFAULT 'observation',
                world_id    TEXT    NOT NULL DEFAULT '',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now', '+08:00'))
            )
            """
        )
        await self._sqlite.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_pc_tick ON memories(pc_id, tick)"
        )
        await self._sqlite.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_world ON memories(world_id)"
        )
        await self._sqlite.commit()
        self._table_ensured = True

    # ── 短期记忆 / Short-term ──
    def _short_queue(self, pc_id: str) -> deque[Memory]:
        if pc_id not in self._short_term:
            self._short_term[pc_id] = deque(maxlen=10)
        return self._short_term[pc_id]

    # ── 存储 / Store ──

    async def store(
        self,
        pc_id: str,
        content: str,
        tick: int,
        importance: int = 2,
        memory_type: str = "observation",
        world_id: str = "",
    ) -> Memory:
        """存储新记忆（短期 + 中期 + 长期）."""
        mem = Memory(
            id=f"mem_{pc_id}_{tick}_{uuid4().hex[:6]}",
            pc_id=pc_id,
            content=content,
            tick=tick,
            importance=importance,
            memory_type=memory_type,
            world_id=world_id,
        )
        self._short_queue(pc_id).append(mem)

        if self._sqlite:
            if not self._table_ensured:
                await self._ensure_table()
            await self._sqlite.execute(
                "INSERT INTO memories (id, pc_id, content, tick, importance, memory_type, world_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    mem.id,
                    mem.pc_id,
                    mem.content,
                    mem.tick,
                    mem.importance,
                    mem.memory_type,
                    mem.world_id,
                ),
            )
            await self._sqlite.commit()

        col_name = _MEM_PREFIX.format(pc_id=pc_id)
        self._chroma.add(
            collection=col_name,
            ids=[mem.id],
            documents=[content],
            metadatas=[
                {"tick": tick, "importance": importance, "type": memory_type, "world_id": world_id}
            ],
        )
        return mem

    async def store_reflection(
        self, pc_id: str, insight: str, tick: int, world_id: str = ""
    ) -> Memory:
        """存储反思洞察（重要性=10）."""
        mem_id = f"reflect_{pc_id}_{tick}_{uuid4().hex[:6]}"
        if self._sqlite:
            if not self._table_ensured:
                await self._ensure_table()
            await self._sqlite.execute(
                "INSERT INTO memories (id, pc_id, content, tick, importance, memory_type, world_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (mem_id, pc_id, insight, tick, 10, "reflection", world_id),
            )
            await self._sqlite.commit()

        col_name = _REFLECT_PREFIX.format(pc_id=pc_id)
        self._chroma.add(
            collection=col_name,
            ids=[mem_id],
            documents=[insight],
            metadatas=[
                {"tick": tick, "importance": 10, "type": "reflection", "world_id": world_id}
            ],
        )
        return Memory(
            id=mem_id,
            pc_id=pc_id,
            content=insight,
            tick=tick,
            importance=10,
            memory_type="reflection",
            world_id=world_id,
        )

    # ── 检索 / Retrieve ──

    async def retrieve(self, pc_id: str, query: str, top_k: int = 5) -> list[Memory]:
        """检索相关记忆（短期全量 + 中期最近 + 长期语义 Top-K）."""
        short = list(self._short_queue(pc_id))

        mid_term: list[Memory] = []
        if self._sqlite:
            if not self._table_ensured:
                await self._ensure_table()
            rows = await self._sqlite.fetch_all(
                "SELECT id, pc_id, content, tick, importance, memory_type, world_id "
                "FROM memories WHERE pc_id = ? ORDER BY tick DESC LIMIT ?",
                (pc_id, top_k),
            )
            mid_term = [_memory_from_row(r) for r in rows]

        col_name = _MEM_PREFIX.format(pc_id=pc_id)
        results = self._chroma.query(collection=col_name, query_text=query, top_k=top_k)
        long_term = [
            Memory(
                id=r["meta"].get("id", ""),
                pc_id=pc_id,
                content=r["text"],
                tick=r["meta"].get("tick", 0),
                importance=r["meta"].get("importance", 1),
                memory_type=r["meta"].get("type", "observation"),
                world_id=r["meta"].get("world_id", ""),
            )
            for r in results
        ]

        # 合并去重（按 id），按重要性降序
        seen: set[str] = set()
        merged: list[Memory] = []
        for m in short + mid_term + long_term:
            if m.id not in seen:
                merged.append(m)
                seen.add(m.id)
        merged.sort(key=lambda m: m.importance, reverse=True)
        return merged[:top_k]

    async def retrieve_reflections(self, pc_id: str, query: str, top_k: int = 3) -> list[Memory]:
        """检索反思记忆（长期反思集合 + 中期 SQLite 反思记录）."""
        col_name = _REFLECT_PREFIX.format(pc_id=pc_id)
        results = self._chroma.query(collection=col_name, query_text=query, top_k=top_k)
        reflections = [
            Memory(
                id=r["meta"].get("id", ""),
                pc_id=pc_id,
                content=r["text"],
                tick=r["meta"].get("tick", 0),
                importance=10,
                memory_type="reflection",
                world_id=r["meta"].get("world_id", ""),
            )
            for r in results
        ]

        if self._sqlite:
            if not self._table_ensured:
                await self._ensure_table()
            rows = await self._sqlite.fetch_all(
                "SELECT id, pc_id, content, tick, importance, memory_type, world_id "
                "FROM memories WHERE pc_id = ? AND memory_type = 'reflection' "
                "ORDER BY tick DESC LIMIT ?",
                (pc_id, top_k),
            )
            sqlite_refs = [_memory_from_row(r) for r in rows]
            # 去重合并
            seen = {m.id for m in reflections}
            for m in sqlite_refs:
                if m.id not in seen:
                    reflections.append(m)
                    seen.add(m.id)
            reflections.sort(key=lambda m: m.importance, reverse=True)
        return reflections[:top_k]

    # ── 生命周期 / Lifecycle ──

    async def drop_character(self, pc_id: str) -> None:
        """删除角色所有记忆."""
        self._short_term.pop(pc_id, None)
        for prefix in [_MEM_PREFIX, _REFLECT_PREFIX]:
            self._chroma.delete_collection(prefix.format(pc_id=pc_id))
        if self._sqlite:
            if not self._table_ensured:
                await self._ensure_table()
            await self._sqlite.execute("DELETE FROM memories WHERE pc_id = ?", (pc_id,))
            await self._sqlite.commit()

    def importance_should_reflect(
        self,
        pc_id: str,
        threshold: int = 100,
    ) -> bool:
        """检查重要性累计是否超阈值."""
        recent = list(self._short_queue(pc_id))
        total = sum(m.importance for m in recent)
        return total >= threshold

    def count(self, pc_id: str) -> int:
        """返回某角色的短期记忆数."""
        return len(self._short_queue(pc_id))


def _memory_from_row(row: dict) -> Memory:
    return Memory(
        id=row["id"],
        pc_id=row["pc_id"],
        content=row["content"],
        tick=row["tick"],
        importance=row["importance"],
        memory_type=row["memory_type"],
        world_id=row.get("world_id", ""),
    )
