"""Tick 指标收集器 / Tick Metrics Collector.

轻量级指标收集，写入 SQLite tick_metrics 表：
- Tick 处理延迟 / Tick processing latency
- LLM 调用次数 + Token 消耗 / LLM call count + Token usage
- Action 类型分布 / Action type distribution
- 估算成本（基于模型定价）/ Estimated cost (model pricing)
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)

# 模型定价（美元/百万 token）/ Model pricing (USD per million tokens)
_MODEL_PRICING: dict[str, dict[str, float]] = {
    "deepseek-chat": {"input": 0.27, "output": 1.10},  # DeepSeek Chat
    "deepseek-v4-flash-free": {"input": 0.0, "output": 0.0},  # Zen Proxy free
    "glm-5.1": {"input": 0.50, "output": 0.50},  # GLM-5.1
    "default": {"input": 0.27, "output": 1.10},  # fallback
}


def estimate_cost(tokens_in: int, tokens_out: int, model: str = "default") -> float:
    """估算单次 LLM 调用成本（美元）/ Estimate single LLM call cost in USD."""
    pricing = _MODEL_PRICING.get(model, _MODEL_PRICING["default"])
    return (tokens_in * pricing["input"] + tokens_out * pricing["output"]) / 1_000_000


@dataclass
class TickMetrics:
    """单个 tick 的指标快照 / Single tick metrics snapshot."""

    tick: int
    world_id: str
    start_time: float = 0.0
    end_time: float = 0.0
    llm_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    events_count: int = 0
    action_types: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors: list[str] = field(default_factory=list)
    model: str = "default"
    stage_latencies: dict[str, float] = field(default_factory=dict)

    @property
    def latency_ms(self) -> float:
        """Tick 处理延迟（毫秒）/ Tick processing latency in ms."""
        if self.end_time <= self.start_time:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    @property
    def estimated_cost_usd(self) -> float:
        """估算成本（美元）/ Estimated cost in USD."""
        return estimate_cost(self.tokens_in, self.tokens_out, self.model)


class MetricsCollector:
    """Tick 指标收集器 / Tick metrics collector.

    收集每个 tick 的性能/Token/成本指标，写入 SQLite tick_metrics 表。
    同时维护内存中的最近 N 次指标用于快速查询。
    """

    # 内存中保留的最大 tick 数 / Max ticks kept in memory
    MAX_RECENT = 100

    def __init__(self, sqlite=None, model: str = "default"):
        self._sqlite = sqlite
        self._model = model
        self._current: dict[str, TickMetrics] = {}  # world_id → TickMetrics
        self._recent: list[TickMetrics] = []
        self._table_ensured = False

    async def initialize(self) -> None:
        """初始化数据库表 / Initialize database table."""
        if self._sqlite and not self._table_ensured:
            await self._ensure_table()

    async def _ensure_table(self) -> None:
        """创建 tick_metrics 表 / Create tick_metrics table."""
        if not self._sqlite:
            return
        await self._sqlite.execute(
            """
            CREATE TABLE IF NOT EXISTS tick_metrics (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                tick              INTEGER NOT NULL,
                world_id          TEXT    NOT NULL,
                latency_ms        REAL    NOT NULL DEFAULT 0,
                llm_calls         INTEGER NOT NULL DEFAULT 0,
                tokens_in         INTEGER NOT NULL DEFAULT 0,
                tokens_out        INTEGER NOT NULL DEFAULT 0,
                events_count      INTEGER NOT NULL DEFAULT 0,
                estimated_cost_usd REAL   NOT NULL DEFAULT 0,
                model             TEXT    NOT NULL DEFAULT '',
                created_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                UNIQUE(tick, world_id)
            )
            """
        )
        await self._sqlite.commit()
        self._table_ensured = True

    def start_tick(self, world_id: str, tick: int) -> None:
        """开始追踪 tick / Start tracking tick."""
        self._current[world_id] = TickMetrics(
            tick=tick, world_id=world_id, start_time=time.monotonic(), model=self._model
        )

    def record_llm(self, world_id: str, tokens_in: int, tokens_out: int) -> None:
        """记录 LLM 调用指标 / Record LLM call metrics."""
        m = self._current.get(world_id)
        if m:
            m.llm_calls += 1
            m.tokens_in += tokens_in
            m.tokens_out += tokens_out

    def record_event(self, world_id: str, event_type: str) -> None:
        """记录事件类型 / Record event type."""
        m = self._current.get(world_id)
        if m:
            m.events_count += 1
            m.action_types[event_type] += 1

    def record_stage_latency(self, world_id: str, stage: str, latency_ms: float) -> None:
        """记录分阶段延迟 / Record per-stage latency."""
        m = self._current.get(world_id)
        if m:
            m.stage_latencies[stage] = latency_ms

    def record_error(self, world_id: str, error: str) -> None:
        """记录错误 / Record error."""
        m = self._current.get(world_id)
        if m:
            m.errors.append(error[:200])

    async def finish_tick(self, world_id: str) -> TickMetrics | None:
        """结束 tick 追踪并持久化 / Finish tick tracking and persist."""
        m = self._current.pop(world_id, None)
        if not m:
            return None
        m.end_time = time.monotonic()

        # 持久化到 SQLite / Persist to SQLite
        if self._sqlite:
            if not self._table_ensured:
                await self._ensure_table()
            await self._sqlite.execute(
                "INSERT OR REPLACE INTO tick_metrics "
                "(tick, world_id, latency_ms, llm_calls, tokens_in, tokens_out, "
                "events_count, estimated_cost_usd, model, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))",
                (
                    m.tick,
                    m.world_id,
                    round(m.latency_ms, 1),
                    m.llm_calls,
                    m.tokens_in,
                    m.tokens_out,
                    m.events_count,
                    round(m.estimated_cost_usd, 8),
                    m.model,
                ),
            )
            await self._sqlite.commit()

        # 维护内存缓存 / Maintain memory cache
        self._recent.append(m)
        if len(self._recent) > self.MAX_RECENT:
            self._recent = self._recent[-self.MAX_RECENT :]

        logger.info(
            "[metrics] tick=%s latency=%.0fms llm=%d tokens=%d/%d cost=$%.6f",
            m.tick,
            m.latency_ms,
            m.llm_calls,
            m.tokens_in,
            m.tokens_out,
            m.estimated_cost_usd,
        )
        return m

    def get_recent(self, world_id: str = "", last_n: int = 20) -> list[dict[str, Any]]:
        """获取最近 N 次 tick 指标 / Get recent N tick metrics."""
        results = self._recent
        if world_id:
            results = [m for m in results if m.world_id == world_id]
        return [
            {
                "tick": m.tick,
                "world_id": m.world_id,
                "latency_ms": round(m.latency_ms, 1),
                "llm_calls": m.llm_calls,
                "tokens_in": m.tokens_in,
                "tokens_out": m.tokens_out,
                "events_count": m.events_count,
                "estimated_cost_usd": round(m.estimated_cost_usd, 8),
                "action_types": dict(m.action_types),
                "errors": m.errors,
                "stage_latencies": dict(m.stage_latencies),
            }
            for m in results[-last_n:]
        ]

    async def get_summary(self, world_id: str = "", last_n: int = 100) -> dict[str, Any]:
        """获取聚合摘要 / Get aggregated summary."""
        recent = self.get_recent(world_id, last_n)
        if not recent:
            return {
                "total_ticks": 0,
                "total_tokens_in": 0,
                "total_tokens_out": 0,
                "total_cost_usd": 0.0,
            }

        total_tokens_in = sum(r["tokens_in"] for r in recent)
        total_tokens_out = sum(r["tokens_out"] for r in recent)
        total_cost = sum(r["estimated_cost_usd"] for r in recent)
        latencies = [r["latency_ms"] for r in recent if r["latency_ms"] > 0]

        # 聚合分阶段延迟 / Aggregate per-stage latencies
        stage_sums: dict[str, list[float]] = defaultdict(list)
        for r in recent:
            for stage, lat in r.get("stage_latencies", {}).items():
                if lat > 0:
                    stage_sums[stage].append(lat)
        avg_stage_latencies = {
            stage: round(sum(lats) / len(lats), 1) for stage, lats in stage_sums.items()
        }

        return {
            "total_ticks": len(recent),
            "total_tokens_in": total_tokens_in,
            "total_tokens_out": total_tokens_out,
            "total_cost_usd": round(total_cost, 8),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
            "avg_tokens_per_tick": round((total_tokens_in + total_tokens_out) / len(recent), 0)
            if recent
            else 0,
            "avg_stage_latencies": avg_stage_latencies,
        }
