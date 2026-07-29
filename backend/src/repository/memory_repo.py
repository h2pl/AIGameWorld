"""记忆仓储 / Memory Repository.

基于 AI Agent 三层记忆系统核心架构：
1. 短期记忆 (Short-Term Memory)：内存 deque（当下的意识流，滑动窗口）
2. 长期记忆 (Long-Term Memory)：SQLite + ChromaDB 双向绑定（陈年旧事与经验，时间衰减+语义打分）
3. 关系记忆/语义网络 (Semantic Memory)：SQLite 结构化关系表（世界观与人设，无需频繁走向量）

对齐 Gemini 提案与 design/04-agent-layer.md §8 + 06-data-layer.md §6。
"""

from collections import deque
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
    """角色记忆存取——短期记忆(deque) + 长期记忆(SQLite+ChromaDB) + 关系记忆(SQLite表) + 反思引擎."""

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
        await self._sqlite.execute(
            """
            CREATE TABLE IF NOT EXISTS semantic_network (
                id          TEXT PRIMARY KEY,
                world_id    TEXT    NOT NULL,
                subject     TEXT    NOT NULL,
                predicate   TEXT    NOT NULL,
                object      TEXT    NOT NULL,
                confidence  REAL    NOT NULL DEFAULT 1.0,
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                UNIQUE(world_id, subject, predicate, object)
            )
            """
        )
        await self._sqlite.execute(
            "CREATE INDEX IF NOT EXISTS idx_semantic_network_subject ON semantic_network(world_id, subject)"
        )

        await self._sqlite.commit()
        self._table_ensured = True

    async def _add_column_if_missing(self, table: str, column: str, definition: str) -> None:
        """如果列不存在则添加 / Add column if it does not exist."""
        rows = await self._sqlite.fetch_all(f"PRAGMA table_info({table})")
        if not any(r.get("name") == column for r in rows):
            await self._sqlite.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _period_for(self, tick: int, current_tick: int) -> str:
        """根据时间间隔决定记忆周期 / Decide memory period by time delta.

        - short_term: 最近 10 tick 内
        - medium_term: 10~50 tick 之间
        - long_term: 超过 50 tick
        """
        delta = max(0, current_tick - tick)
        if delta <= 10:
            return "short_term"
        elif delta <= 50:
            return "medium_term"
        return "long_term"

    # ── 1. 短期记忆 / Short-Term Memory ──
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
        current_tick: int = 0,
    ) -> Memory:
        """存储新记忆.

        短期记忆（delta ≤ 10 tick）：仅入 deque，不持久化。
        中期/长期记忆（delta > 10 tick）：deque + SQLite + ChromaDB 三写。
        period 由时间间隔自动计算，除非外部显式指定。
        """
        resolved_period = period or self._period_for(tick, current_tick)
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
        # 所有记忆都入短期窗口 / All memories enter short-term window
        self._short_queue(pc_id).append(mem)

        # 短期记忆不落盘 / Short-term memories stay in-memory only
        if resolved_period == "short_term":
            return mem

        # 中/长期记忆双写 / Medium/long-term: persist to SQLite + ChromaDB
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

    def get_short_term(self, pc_id: str) -> list[Memory]:
        """读取短期记忆（deque 窗口，最近 10 条）/ Read short-term memory from deque."""
        return list(self._short_queue(pc_id))

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

    # ── 3. 关系记忆 / Semantic Memory (Phase 2) ──
    @traced()
    async def upsert_relation(
        self,
        world_id: str,
        subject: str,
        predicate: str,
        object_: str,
        confidence: float = 1.0,
    ) -> None:
        """更新或插入一条语义关系 / Upsert a semantic relation (Triple)."""
        if not self._sqlite:
            return
        if not self._table_ensured:
            await self._ensure_table()

        rel_id = f"rel_{uuid4().hex[:8]}"
        await self._sqlite.execute(
            """
            INSERT INTO semantic_network (id, world_id, subject, predicate, object, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(world_id, subject, predicate, object)
            DO UPDATE SET
                confidence = excluded.confidence,
                updated_at = datetime('now', 'localtime')
            """,
            (rel_id, world_id, subject, predicate, object_, confidence),
        )
        await self._sqlite.commit()

    @traced()
    async def get_relations_for(self, world_id: str, subject: str) -> list[dict]:
        """获取某主体的所有语义关系 / Get all semantic relations for a subject."""
        if not self._sqlite:
            return []
        if not self._table_ensured:
            await self._ensure_table()

        rows = await self._sqlite.fetch_all(
            "SELECT predicate, object, confidence FROM semantic_network WHERE world_id = ? AND subject = ?",
            (world_id, subject),
        )
        return [dict(r) for r in rows]

    @traced()
    async def delete_relation(
        self, world_id: str, subject: str, predicate: str, object_: str
    ) -> None:
        """删除一条语义关系 / Delete a semantic relation."""
        if not self._sqlite:
            return
        if not self._table_ensured:
            await self._ensure_table()

        await self._sqlite.execute(
            "DELETE FROM semantic_network WHERE world_id = ? AND subject = ? AND predicate = ? AND object = ?",
            (world_id, subject, predicate, object_),
        )
        await self._sqlite.commit()

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
        """返回某角色的工作记忆数."""
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
