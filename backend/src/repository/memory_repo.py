"""记忆仓储 / Memory Repository.

基于认知科学四层记忆模型：
1. 感知缓冲 (Perception)：当前 tick 输入，由 state 承载
2. 情景记忆 (Episodic)：SQLite + ChromaDB 全量持久化，三要素精排检索
3. 反思记忆 (Reflective)：ChromaDB + SQLite 双写，LLM 蒸馏洞察
4. 语义记忆 (Semantic)：Neo4j 关系图谱

所有记忆立即双写，无内存缓存层。
"""

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
    similarity: float = 1.0,
    alpha: float = 1.0,  # 语义相关度权重 (Relevance)
    beta: float = 1.0,  # 时间衰减权重 (Recency)
    gamma: float = 1.0,  # 重要度权重 (Importance)
    half_life: int = 10,  # 时间衰减半衰期
) -> float:
    """计算长时记忆的三要素综合检索分数 (Relevance + Recency + Importance).

    公式: Score = α * Relevance + β * Recency + γ * Importance
    """
    if current_tick <= 0:
        return float(base_importance)

    # 1. Relevance: ChromaDB 的相似度分数，归一化到 0-1 之间
    relevance_score = max(0.0, min(1.0, similarity))

    # 2. Recency: 指数衰减，时间越久远，分数越趋近于 0
    delta = max(0, current_tick - memory_tick)
    recency_score = 0.5 ** (delta / half_life) if half_life > 0 else 1.0

    # 3. Importance: 基础重要度归一化到 0-1 之间 (假设满分是 10)
    importance_score = min(1.0, base_importance / 10.0)

    # 综合算分
    return (alpha * relevance_score) + (beta * recency_score) + (gamma * importance_score)


class MemoryRepo:
    """角色记忆存取——情景记忆(SQLite+ChromaDB) + 反思记忆(ChromaDB+SQLite)."""

    def __init__(self, chroma: ChromaClient, sqlite=None):
        self._chroma = chroma
        self._sqlite = sqlite
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
        current_tick: int = 0,
    ) -> Memory:
        """存储新记忆（全量持久化）.

        所有记忆立即双写 SQLite + ChromaDB，deque 仅作为注意力窗口缓存。
        不再区分短期/长期——时间维度仅作为检索时的 recency 评分因子。
        """
        mem = Memory(
            id=f"mem_{pc_id}_{tick}_{uuid4().hex[:6]}",
            pc_id=pc_id,
            content=content,
            tick=tick,
            importance=importance,
            memory_type=memory_type,
            period=period or "episodic",
            entity_type=entity_type,
            world_id=world_id,
        )
        # 全量持久化：SQLite + ChromaDB / Persist to both stores
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
                    "entity_type": entity_type,
                    "world_id": world_id,
                }
            ],
        )
        return mem

    @traced()
    async def store_reflection(
        self,
        pc_id: str,
        insight: str,
        tick: int,
        world_id: str = "",
        entity_type: str = "pc",
        current_tick: int = 0,
    ) -> Memory:
        """存储反思洞察（重要性=10，ChromaDB + SQLite 双写）.

        反思记忆固定为 long_term — 反思是对过去经验的抽象总结，不应随时间降级。
        """
        mem_id = f"reflect_{pc_id}_{tick}_{uuid4().hex[:6]}"
        period = "long_term"

        # 1. ChromaDB 向量写入（语义检索路径）/ ChromaDB vector write
        col_name = _REFLECT_PREFIX.format(pc_id=pc_id)
        self._chroma.add(
            collection=col_name,
            ids=[mem_id],
            documents=[insight],
            metadatas=[
                {
                    "id": mem_id,
                    "tick": tick,
                    "importance": 10,
                    "type": "reflection",
                    "period": period,
                    "entity_type": entity_type,
                    "world_id": world_id,
                }
            ],
        )

        # 2. SQLite 结构化写入（精确查询/审计/聚合）/ SQLite structured write
        if self._sqlite:
            if not self._table_ensured:
                await self._ensure_table()
            await self._sqlite.execute(
                "INSERT INTO memories (id, pc_id, content, tick, importance, memory_type, period, entity_type, world_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (mem_id, pc_id, insight, tick, 10, "reflection", period, entity_type, world_id),
            )
            await self._sqlite.commit()

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

    async def get_recent(self, pc_id: str, limit: int = 10) -> list[Memory]:
        """从 SQLite 读取最近 N 条记忆（按 tick 倒序）/ Recent memories from SQLite."""
        if not self._sqlite:
            return []
        if not self._table_ensured:
            await self._ensure_table()
        rows = await self._sqlite.fetch_all(
            "SELECT id, pc_id, content, tick, importance, memory_type, period, entity_type, world_id "
            "FROM memories WHERE pc_id = ? AND memory_type != 'reflection' "
            "ORDER BY tick DESC, rowid DESC LIMIT ?",
            (pc_id, limit),
        )
        return [_memory_from_row(r) for r in rows]

    def search_long_term_vector(self, pc_id: str, query: str, top_k: int = 15) -> list[dict]:
        """ChromaDB 语义检索长期记忆 / Semantic search long-term memory via ChromaDB.

        返回 {text, meta, distance} 字典列表。
        """
        col_name = _MEM_PREFIX.format(pc_id=pc_id)
        return self._chroma.query(collection=col_name, query_text=query, top_k=top_k)

    async def fetch_long_term_sqlite(self, ids: list[str]) -> list[Memory]:
        """从 SQLite 按 ID 批量读取长期记忆 / Fetch long-term memory by IDs from SQLite."""
        if not ids or not self._sqlite:
            return []
        if not self._table_ensured:
            await self._ensure_table()
        placeholders = ",".join("?" * len(ids))
        sql = f"SELECT id, pc_id, content, tick, importance, memory_type, period, entity_type, world_id FROM memories WHERE id IN ({placeholders})"  # noqa: S608
        rows = await self._sqlite.fetch_all(sql, tuple(ids))
        return [_memory_from_row(r) for r in rows]

    @traced()
    async def retrieve_reflections(
        self,
        pc_id: str,
        query: str,
        top_k: int = 3,
        current_tick: int = 0,
        min_tick: int | None = None,
    ) -> list[Memory]:
        """检索反思记忆（ChromaDB 语义检索 + 可选 tick 过滤）/ Retrieve reflection memories.

        Args:
            pc_id: 角色 ID
            query: 语义查询文本（应为当前情境描述，空字符串则退化为最近优先）
            top_k: 返回条数
            current_tick: 当前 tick（用于三要素评分）
            min_tick: 仅返回 tick >= min_tick 的反思（精确过滤）
        """
        col_name = _REFLECT_PREFIX.format(pc_id=pc_id)
        # 多召回一些，过滤后再截断 / Over-fetch to compensate for post-filter
        fetch_k = top_k * 2 if min_tick is not None else top_k
        results = self._chroma.query(
            collection=col_name, query_text=query or "recent", top_k=fetch_k
        )
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
        # tick 精确过滤 / Tick filter
        if min_tick is not None:
            reflections = [m for m in reflections if m.tick >= min_tick]
        reflections.sort(
            key=lambda m: score_memory(m.importance, m.tick, current_tick, similarity=1.0),
            reverse=True,
        )
        return reflections[:top_k]

    async def get_last_reflection_tick(self, pc_id: str) -> int:
        """从 SQLite 精确查询角色最近一次反思的 tick / Get last reflection tick from SQLite."""
        if not self._sqlite:
            return 0
        if not self._table_ensured:
            await self._ensure_table()
        rows = await self._sqlite.fetch_all(
            "SELECT MAX(tick) as last_tick FROM memories WHERE pc_id = ? AND memory_type = 'reflection'",
            (pc_id,),
        )
        if rows and rows[0]["last_tick"] is not None:
            return rows[0]["last_tick"]
        return 0

    # ── 生命周期 / Lifecycle ──

    @traced()
    async def drop_character(self, pc_id: str) -> None:
        """删除角色所有记忆."""
        for prefix in [_MEM_PREFIX, _REFLECT_PREFIX]:
            self._chroma.delete_collection(prefix.format(pc_id=pc_id))
        if self._sqlite:
            if not self._table_ensured:
                await self._ensure_table()
            await self._sqlite.execute("DELETE FROM memories WHERE pc_id = ?", (pc_id,))
            await self._sqlite.commit()

    async def importance_should_reflect(
        self,
        pc_id: str,
        threshold: int = 100,
        since_tick: int = 0,
    ) -> bool:
        """检查自上次反思以来重要性累计是否超阈值."""
        if not self._sqlite:
            return False
        if not self._table_ensured:
            await self._ensure_table()
        rows = await self._sqlite.fetch_all(
            "SELECT COALESCE(SUM(importance), 0) as total FROM memories "
            "WHERE pc_id = ? AND tick > ? AND memory_type != 'reflection'",
            (pc_id, since_tick),
        )
        total = rows[0]["total"] if rows else 0
        return total >= threshold


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
