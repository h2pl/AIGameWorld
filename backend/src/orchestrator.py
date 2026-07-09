"""编排器 / Orchestrator: 全局单例，管理多个 world 的 tick 执行.

每个 tick 使用独立的 thread_id，避免累加器字段跨 tick 累积.
同一 world 的 tick 执行加互斥锁，防止并发导致 data_tick 重复或事件重复写入."""

import asyncio
import time
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver

from src.graph import checkpoints
from src.graph.graph import OverallState, build_tick_graph
from src.utils.graph_callbacks import TickGraphCallback
from src.utils.logging import get_logger, log_phase

logger = get_logger(__name__)


class Orchestrator:
    """全局 TickGraph 编排器——一个实例处理所有 world."""

    def __init__(
        self,
        checkpointer: BaseCheckpointSaver | None = None,
        llm: Any = None,
        reflection_interval: int = 5,
        repos: Any = None,
        metrics_collector=None,
    ):
        logger.info("[orchestrator] init")
        if repos is None:
            logger.error("[orchestrator] repos is required")
        self._graph = build_tick_graph()
        self._checkpointer = checkpointer or checkpoints.create_dev_checkpointer()
        self._app = self._graph.compile(checkpointer=self._checkpointer)
        self._llm = llm
        self._reflection_interval = reflection_interval
        self._repos = repos
        self._metrics = metrics_collector  # 指标收集器 / Metrics collector
        self._locks: dict[str, asyncio.Lock] = {}

    async def run_tick(self, world_id: str) -> dict:
        """对指定 world 执行一个完整 Tick——data_tick 从 worlds 表读取并自增."""
        lock = self._locks.setdefault(world_id, asyncio.Lock())
        async with lock:
            world_repo = self._repos.get("world")
            if not world_repo:
                logger.error("[orchestrator] world repo not found")
                raise RuntimeError("world repo not found")

            tick = await world_repo.increment_data_tick(world_id)

            initial_state: OverallState = {"tick": tick, "world_id": world_id}

            config = self._make_config(world_id, tick)
            callbacks = [
                TickGraphCallback(tick=tick, world_id=world_id, metrics_collector=self._metrics)
            ]
            # 链路追踪：注入 Langfuse handler / Tracing: inject Langfuse handler
            from src.utils.tracing import create_langfuse_handler, get_langfuse_metadata

            langfuse_handler = create_langfuse_handler(tick, world_id)
            if langfuse_handler:
                callbacks.append(langfuse_handler)
                # v4：通过 metadata 传递 trace 元数据 / v4: pass trace metadata via metadata
                config["metadata"] = get_langfuse_metadata(tick, world_id)
            config["callbacks"] = callbacks

            # 指标收集：开始追踪 / Metrics: start tracking
            if self._metrics:
                self._metrics.start_tick(world_id, tick)

            # 设置 LLM 客户端的 world_id 上下文，供 token 指标收集 / Set world_id context for LLM token metrics
            if self._llm and hasattr(self._llm, "set_context"):
                self._llm.set_context(world_id)

            t_start = time.monotonic()
            try:
                result: dict[str, Any] | Any = await self._app.ainvoke(initial_state, config)
            except Exception as e:
                if self._metrics:
                    self._metrics.record_error(world_id, str(e))
                raise
            log_phase("tick", tick, elapsed=time.monotonic() - t_start)

            # 指标收集：结束追踪 / Metrics: finish tracking
            if self._metrics:
                await self._metrics.finish_tick(world_id)

            return {"tick": result["tick"]}

    def _make_config(self, world_id: str, tick: int) -> dict:
        """构造 LangGraph 执行配置 / Build LangGraph run config."""
        # 每个 tick 使用独立 thread_id，避免累加器字段跨 tick 累积
        # run_name 统一为 {world_id}__tick_{tick}，LangSmith/Langfuse 面板一致
        config: dict[str, Any] = {
            "configurable": {
                "thread_id": f"{world_id}__tick_{tick}",
                "repos": self._repos,
            },
            "run_name": f"{world_id}__tick_{tick}",
        }
        if self._llm:
            config["configurable"]["llm"] = self._llm
            config["configurable"]["reflection_interval"] = self._reflection_interval
            config["configurable"]["mock"] = getattr(self._llm, "_mock", False)
        return config

    async def reset(self, world_id: str) -> None:
        """重置 world：清零 tick + 清理事件/DM记录/摘要 + 重置角色坐标 + 清空 checkpoint."""
        # 1. 清零 tick / Reset ticks to 0
        world_repo = self._repos.get("world")
        if not world_repo:
            logger.error("[orchestrator] world repo not found")
            raise RuntimeError("world repo not found")
        await world_repo.reset_tick(world_id)

        # 2. 清空 tick 事件 / Clear tick events
        event_repo = self._repos.get("event")
        if event_repo:
            await event_repo.delete_by_world(world_id)

        # 3. 清空 DM 记录 + 摘要 / Clear DM records and summaries
        dm_repo = self._repos.get("dm_record")
        if dm_repo:
            await dm_repo.delete_by_world(world_id)
            await dm_repo.delete_summaries_by_world(world_id)

        # 4. 重置 PC 坐标 / Reset PC positions
        pc_repo = self._repos.get("char")
        if pc_repo:
            await pc_repo.reset_positions(world_id)

        # 5. 清空 LangGraph checkpoint（避免旧 state 残留）/ Clear LangGraph checkpoints
        self._checkpointer = checkpoints.create_dev_checkpointer()
        self._app = self._graph.compile(checkpointer=self._checkpointer)

        logger.info("[orchestrator] reset complete for %s", world_id)
