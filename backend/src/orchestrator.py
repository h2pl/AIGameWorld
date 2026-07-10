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

            # Langfuse 追踪（官方推荐方式）/ Langfuse tracing (official recommended pattern)
            # 文档：https://langfuse.com/docs/observability/features/sessions
            # start_as_current_observation 创建 root span → propagate_attributes 设置
            # session_id/user_id/tags → CallbackHandler 自动挂到 root span 下
            # / start_as_current_observation creates root span → propagate_attributes sets
            # session_id/user_id/tags → CallbackHandler auto-attaches under root span
            from src.utils.tracing import create_langfuse_handler

            langfuse_handler = create_langfuse_handler(tick, world_id)
            if langfuse_handler:
                callbacks.append(langfuse_handler)
            config["callbacks"] = callbacks

            # 指标收集：开始追踪 / Metrics: start tracking
            if self._metrics:
                self._metrics.start_tick(world_id, tick)

            # 设置 LLM 客户端的 world_id 上下文，供 token 指标收集 / Set world_id context for LLM token metrics
            if self._llm and hasattr(self._llm, "set_context"):
                self._llm.set_context(world_id)

            t_start = time.monotonic()
            try:
                if langfuse_handler:
                    # 官方推荐：start_as_current_observation + propagate_attributes
                    from langfuse import get_client, propagate_attributes

                    langfuse = get_client()
                    trace_name = f"{world_id}__tick_{tick}"
                    with langfuse.start_as_current_observation(as_type="span", name="run_tick"):
                        with propagate_attributes(
                            trace_name=trace_name,
                            tags=[f"world:{world_id}", f"tick:{tick}"],
                        ):
                            result: dict[str, Any] | Any = await self._app.ainvoke(initial_state, config)
                else:
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

    async def get_state(self, world_id: str, tick: int) -> dict[str, Any] | None:
        """获取某个特定 Tick 结束时的世界状态快照 / Get the state snapshot of a specific tick."""
        thread_id = f"{world_id}__tick_{tick}"
        config = {"configurable": {"thread_id": thread_id}}
        state_snapshot = await self._app.aget_state(config)
        if not state_snapshot:
            return None
        return state_snapshot.values

    async def get_state_history(self, world_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """获取最近的历史快照列表 / Get recent history of state snapshots."""
        # 注意: 因为我们在 _make_config 里用了每个 tick 独立的 thread_id
        # 这里需要遍历最近的几个 tick 来查各自的 thread_id
        world_repo = self._repos.get("world")
        current_tick = await world_repo.get_data_tick(world_id)
        
        history = []
        for t in range(current_tick, max(0, current_tick - limit), -1):
            state = await self.get_state(world_id, t)
            if state:
                history.append(state)
        return history

    async def rewind_to_tick(self, world_id: str, target_tick: int) -> None:
        """时光倒流：将世界状态回滚到特定的 tick / Rewind world to a specific tick."""
        world_repo = self._repos.get("world")
        current_tick = await world_repo.get_data_tick(world_id)
        
        if target_tick >= current_tick or target_tick <= 0:
            raise ValueError(f"Invalid target tick {target_tick}")

        # 1. 恢复 World 数据表的 data_tick
        await world_repo.set_data_tick(world_id, target_tick)

        # 2. 清理数据库中大于 target_tick 的所有未来数据
        # 清理未来的事件
        event_repo = self._repos.get("event")
        if event_repo:
            await event_repo._db.execute("DELETE FROM tick_events WHERE world_id = ? AND tick > ?", (world_id, target_tick))
            await event_repo._db.commit()

        # 清理未来的 DM 记录和摘要
        dm_repo = self._repos.get("dm_record")
        if dm_repo:
            await dm_repo._db.execute("DELETE FROM dm_records WHERE world_id = ? AND tick > ?", (world_id, target_tick))
            await dm_repo._db.execute("DELETE FROM story_summaries WHERE world_id = ? AND tick > ?", (world_id, target_tick))
            await dm_repo._db.commit()
            
        # 清理未来的记忆
        memory_repo = self._repos.get("memory")
        if memory_repo:
            await memory_repo._sqlite.execute("DELETE FROM memories WHERE world_id = ? AND tick > ?", (world_id, target_tick))
            await memory_repo._sqlite.commit()

        logger.info(f"[orchestrator] Rewound world {world_id} to tick {target_tick}")
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
