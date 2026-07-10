"""记忆仓储 / Memory Repository.

基于三层记忆架构：
- 短期：内存 deque（每角色最近 10 条 observation）
- 中期：SQLite `memories` 表（按角色/世界持久化）
- 长期：ChromaDB（语义检索 + 反思集合）

对齐 design/04-agent-layer.md §8 + 06-data-layer.md §6。
"""

from collections import deque
from typing import Any
from uuid import uuid4

from ..domain.memory import Memory
from ..storage.chroma_client import ChromaClient
from ..utils.logging import get_logger
from ..utils.tracing import traced

logger = get_logger(__name__)

_MEM_PREFIX = "mem_{pc_id}"
_REFLECT_PREFIX = "reflect_{pc_id}"


def score_memory(
    base_importance: int,
    memory_tick: int,
    current_tick: int,
    half_life: int = 10,
    recent_window: int = 2,
    recent_boost: float = 1.5,
) -> float:
    """计算记忆综合重要性分数 / Compute composite memory importance score.

    - base_importance: 事件类型决定的基础重要性（1-10）。
    - 时间衰减: 以 half_life 为半衰期做指数衰减。
    - 近期加成: current_tick - memory_tick <= recent_window 时乘以加成。
    """
    if current_tick <= 0:
        return float(base_importance)
    delta = max(0, current_tick - memory_tick)
    decay = 0.5 ** (delta / half_life) if half_life > 0 else 1.0
    boost = recent_boost if delta <= recent_window else 1.0
    return base_importance * decay * boost


class MemoryRepo:
    """角色记忆存取——短期(deque) + 中期(SQLite) + 长期(ChromaDB) + 反思(ChromaDB)."""

    def __init__(self, chroma: ChromaClient, sqlite=None):
        self._chroma = chroma
        self._sqlite = sqlite
        self._short_term: dict[str, deque[Memory]] = {}  # pc_id → 最近10条
        self._table_ensured = False

    # ── 表初始化 / Table init ──
    @traced()
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
                period      TEXT    NOT NULL DEFAULT 'medium_term',
                entity_type TEXT    NOT NULL DEFAULT 'pc',
                world_id    TEXT    NOT NULL DEFAULT '',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        # 兼容旧表：动态添加新列 / Migrate old tables
        await self._add_column_if_missing(
            "memories", "period", "TEXT NOT NULL DEFAULT 'medium_term'"
        )
        await self._add_column_if_missing("memories", "entity_type", "TEXT NOT NULL DEFAULT 'pc'")
        await self._sqlite.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_pc_tick ON memories(pc_id, tick)"
        )
        await self._sqlite.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_world ON memories(world_id)"
        )
        await self._sqlite.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)"
        )
        await self._sqlite.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_period ON memories(period)"
        )
        await self._sqlite.commit()
        self._table_ensured = True

    async def _add_column_if_missing(self, table: str, column: str, definition: str) -> None:
        """如果列不存在则添加 / Add column if it does not exist."""
        rows = await self._sqlite.fetch_all(f"PRAGMA table_info({table})")
        if not any(r.get("name") == column for r in rows):
            await self._sqlite.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _period_for(self, importance: int, memory_type: str) -> str:
        """根据重要性和类型决定记忆周期 / Decide memory period."""
        if memory_type == "reflection":
            return "long_term"
        if importance >= 7:
            return "long_term"
        if importance <= 2:
            return "short_term"
        return "medium_term"

    # ── 短期记忆 / Short-term ──
    def _short_queue(self, pc_id: str) -> deque[Memory]:
        if pc_id not in self._short_term:
            self._short_term[pc_id] = deque(maxlen=10)
        return self._short_term[pc_id]

    # ── 存储 / Store ──

    @traced()
    async def store(
        self,
        pc_id: str,
        content: str,
        tick: int,
        importance: int = 2,
        memory_type: str = "observation",
        period: str = "",
        entity_type: str = "pc",
        world_id: str = "",
    ) -> Memory:
        """存储新记忆（短期 + 中期 + 长期）."""
        resolved_period = period or self._period_for(importance, memory_type)
        mem = Memory(
            id=f"mem_{pc_id}_{tick}_{uuid4().hex[:6]}",
            pc_id=pc_id,
            content=content,
            tick=tick,
            importance=importance,
            memory_type=memory_type,
            period=resolved_period,
            entity_type=entity_type,
            world_id=world_id,
        )
        self._short_queue(pc_id).append(mem)

        if self._sqlite:
            if not self._table_ensured:
                await self._ensure_table()
            await self._sqlite.execute(
                "INSERT INTO memories (id, pc_id, content, tick, importance, memory_type, period, entity_type, world_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    mem.id,
                    mem.pc_id,
                    mem.content,
                    mem.tick,
                    mem.importance,
                    mem.memory_type,
                    mem.period,
                    mem.entity_type,
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
                {
                    "tick": tick,
                    "importance": importance,
                    "type": memory_type,
                    "period": resolved_period,
                    "entity_type": entity_type,
                    "world_id": world_id,
                }
            ],
        )
        return mem

    @traced()
    async def store_reflection(
        self, pc_id: str, insight: str, tick: int, world_id: str = "", entity_type: str = "pc"
    ) -> Memory:
        """存储反思洞察（重要性=10）."""
        mem_id = f"reflect_{pc_id}_{tick}_{uuid4().hex[:6]}"
        period = "long_term"
        if self._sqlite:
            if not self._table_ensured:
                await self._ensure_table()
            await self._sqlite.execute(
                "INSERT INTO memories (id, pc_id, content, tick, importance, memory_type, period, entity_type, world_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (mem_id, pc_id, insight, tick, 10, "reflection", period, entity_type, world_id),
            )
            await self._sqlite.commit()

        col_name = _REFLECT_PREFIX.format(pc_id=pc_id)
        self._chroma.add(
            collection=col_name,
            ids=[mem_id],
            documents=[insight],
            metadatas=[
                {
                    "tick": tick,
                    "importance": 10,
                    "type": "reflection",
                    "period": period,
                    "entity_type": entity_type,
                    "world_id": world_id,
                }
            ],
        )
        return Memory(
            id=mem_id,
            pc_id=pc_id,
            content=insight,
            tick=tick,
            importance=10,
            memory_type="reflection",
            period=period,
            entity_type=entity_type,
            world_id=world_id,
        )

    # ── 检索 / Retrieve ──

    @traced()
    async def retrieve(
        self,
        pc_id: str,
        query: str,
        top_k: int = 5,
        memory_types: list[str] | None = None,
        periods: list[str] | None = None,
        entity_types: list[str] | None = None,
        current_tick: int = 0,
    ) -> list[Memory]:
        """检索相关记忆（短期全量 + 中期最近 + 长期语义 Top-K），支持类型/周期/实体过滤，按综合重要性分数排序."""
        short = list(self._short_queue(pc_id))

        mid_term: list[Memory] = []
        if self._sqlite:
            if not self._table_ensured:
                await self._ensure_table()
            where = "WHERE pc_id = ?"
            params: list[Any] = [pc_id]
            if memory_types:
                placeholders = ",".join("?" * len(memory_types))
                where += f" AND memory_type IN ({placeholders})"
                params.extend(memory_types)
            if periods:
                placeholders = ",".join("?" * len(periods))
                where += f" AND period IN ({placeholders})"
                params.extend(periods)
            if entity_types:
                placeholders = ",".join("?" * len(entity_types))
                where += f" AND entity_type IN ({placeholders})"
                params.extend(entity_types)
            sql = f"SELECT id, pc_id, content, tick, importance, memory_type, period, entity_type, world_id FROM memories {where} ORDER BY tick DESC LIMIT ?"  # noqa: S608
            params.append(top_k)
            rows = await self._sqlite.fetch_all(sql, tuple(params))
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
                period=r["meta"].get("period", "medium_term"),
                entity_type=r["meta"].get("entity_type", "pc"),
                world_id=r["meta"].get("world_id", ""),
            )
            for r in results
        ]

        def _matches_filters(m: Memory) -> bool:
            return (
                (not memory_types or m.memory_type in memory_types)
                and (not periods or m.period in periods)
                and (not entity_types or m.entity_type in entity_types)
            )

        # 合并去重（按 id），按综合重要性分数降序
        seen: set[str] = set()
        merged: list[Memory] = []
        for m in short + mid_term + long_term:
            if m.id not in seen and _matches_filters(m):
                merged.append(m)
                seen.add(m.id)
        merged.sort(
            key=lambda m: score_memory(m.importance, m.tick, current_tick),
            reverse=True,
        )
        return merged[:top_k]

    @traced()
    async def retrieve_reflections(
        self, pc_id: str, query: str, top_k: int = 3, current_tick: int = 0
    ) -> list[Memory]:
        """检索反思记忆（长期反思集合 + 中期 SQLite 反思记录），按综合重要性分数排序."""
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
            reflections.sort(
                key=lambda m: score_memory(m.importance, m.tick, current_tick),
                reverse=True,
            )
        return reflections[:top_k]

    # ── 生命周期 / Lifecycle ──

    @traced()
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
        period=row.get("period", "medium_term"),
        entity_type=row.get("entity_type", "pc"),
        world_id=row.get("world_id", ""),
    )
